import asyncio
import pytest
import time
from unittest.mock import patch, AsyncMock
from core.fsm import instance as fsm
from core.state_guard import guard
from core.state import State

@pytest.fixture(autouse=True)
async def setup_fsm():
    # Setup: Register default handlers
    # We use OBSERVE -> ERROR -> IDLE transition chain
    # because OBSERVE -> IDLE is forbidden by StateGuard.
    
    async def observe_handler(context):
        return State.ERROR
        
    async def error_handler(context):
        return State.IDLE
    
    # Store original handlers to restore later
    original_handlers = fsm.state_handlers.copy()
    
    # Register Mocks
    fsm.register_handler(State.OBSERVE, AsyncMock(execute=observe_handler))
    fsm.register_handler(State.ERROR, AsyncMock(execute=error_handler))
    
    # Also register generic handlers for other states if needed to avoid crashes
    fsm.register_handler(State.RETRIEVE, AsyncMock(execute=lambda c: State.ERROR))
    fsm.register_handler(State.PLAN, AsyncMock(execute=lambda c: State.ERROR))
    
    yield
    
    # Teardown: Restore original handlers
    fsm.state_handlers = original_handlers
    # Clear locks
    guard._user_locks.clear()

@pytest.mark.asyncio
async def test_concurrent_messages_same_user():
    """
    Два конкурентні повідомлення від user_id=999 не повинні race.
    """
    user_id = 999
    
    # Needs to be slightly slow to allow race possibilities if not locked
    async def slow_observe(context):
        await asyncio.sleep(0.1)
        return State.ERROR # Valid transition

    async def error_handler(context):
        return State.IDLE

    fsm.register_handler(State.OBSERVE, AsyncMock(execute=slow_observe))
    fsm.register_handler(State.ERROR, AsyncMock(execute=error_handler))
    
    async def send_message(text):
        return await fsm.process_event({
            "user_id": user_id,
            "type": "message",
            "text": text
        })
    
    # Запустити паралельно
    results = await asyncio.gather(
        send_message("Повідомлення 1"),
        send_message("Повідомлення 2")
    )
    
    # Обидва повинні завершитися успішно
    assert len(results) == 2
    assert all(r.errors == [] for r in results)
    
    # State should be IDLE after processing
    assert guard.get_state(user_id) == State.IDLE

@pytest.mark.asyncio
async def test_different_users_parallel():
    """
    Повідомлення від різних користувачів повинні обробляться паралельно.
    """
    async def slow_handler(context):
        await asyncio.sleep(0.5)
        return State.ERROR # Valid transition

    fsm.register_handler(State.OBSERVE, AsyncMock(execute=slow_handler))
    
    async def send_slow_message(user_id):
        start = time.time()
        await fsm.process_event({
            "user_id": user_id,
            "type": "message",
            "text": "Test"
        })
        return time.time() - start
    
    # Запустити 3 користувачів паралельно
    start_total = time.time()
    times = await asyncio.gather(
        send_slow_message(101),
        send_slow_message(102),
        send_slow_message(103)
    )
    total_time = time.time() - start_total
    max_single_time = max(times)
    
    print(f"Total: {total_time}, Max Single: {max_single_time}")
    assert total_time < (max_single_time * 3) * 0.8

@pytest.mark.asyncio
async def test_lock_timeout_prevents_deadlock():
    """
    Якщо state handler зависає, timeout повинен спрацювати.
    """
    user_id = 888
    
    # Setup: Lock held manually
    await guard._get_lock(user_id) 
    lock = await guard._get_lock(user_id)
    await lock.acquire()
    
    try:
        # Mock fast timeout
        original_timeout = asyncio.timeout
        def fast_timeout(delay):
            return original_timeout(0.1) 
            
        with patch('asyncio.timeout', side_effect=fast_timeout):
             with pytest.raises(RuntimeError, match="acquisition timeout"):
                await fsm.process_event({
                    "user_id": user_id,
                    "type": "message",
                    "text": "Test"
                })

    finally:
        if lock.locked():
            lock.release()
            
    # Check error state - IT RESETS TO IDLE IN FINALLY
    assert guard.get_state(user_id) == State.IDLE

@pytest.mark.asyncio
async def test_lock_cleanup():
    """
    Locks повинні видалятися після завершення потоку.
    """
    user_id = 777
    
    await fsm.process_event({
        "user_id": user_id,
        "type": "message",
        "text": "Test"
    })
    
    # Lock повинен бути видалений
    assert user_id not in guard._user_locks

@pytest.mark.asyncio
async def test_security_limit():
    """
    StateGuard повинен обмежувати кількість активних locks (MAX_CONCURRENT_USERS).
    """
    import config
    original_limit = config.MAX_CONCURRENT_USERS
    config.MAX_CONCURRENT_USERS = 5
    
    try:
        # Створити 5 locks
        for i in range(5):
            await guard._get_lock(i)
            
        # 6-й повинен викликати помилку
        with pytest.raises(RuntimeError, match="SECURITY BLOCK"):
            await guard._get_lock(6)
    finally:
        config.MAX_CONCURRENT_USERS = original_limit
        guard._user_locks.clear()

@pytest.mark.asyncio
async def test_concurrent_cleanup():
    """
    Concurrent calls to cleanup_user_lock should be safe.
    """
    user_id = 555
    await guard._get_lock(user_id)
    
    # Call multiple times
    guard.cleanup_user_lock(user_id)
    guard.cleanup_user_lock(user_id) # Should not raise KeyError
    
    assert user_id not in guard._user_locks
