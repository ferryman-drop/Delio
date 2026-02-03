import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from core.fsm import instance as fsm
from core.state_guard import guard
from core.state import State
import core.fsm as fsm_module

@pytest.fixture(autouse=True)
async def setup_fsm():
    # Similar setup to prev task, but focus on the specific handlers needed
    guard._user_states.clear()
    guard._user_locks.clear()
    
    original_handlers = fsm.state_handlers.copy()
    
    # Defaults
    async def default_handler(context):
        return State.IDLE
    fsm.register_handler(State.OBSERVE, AsyncMock(execute=default_handler))
    fsm.register_handler(State.ERROR, AsyncMock(execute=lambda c: State.IDLE))
    
    yield
    fsm.state_handlers = original_handlers
    guard._user_locks.clear()

@pytest.mark.asyncio
async def test_infinite_loop_trap():
    """
    Test that the FSM prevents infinite loops if a state keeps returning itself or cycling indefinitely.
    """
    user_id = 111
    
    # Handler that loops OBSERVE -> OBSERVE is invalid in Guard unless we bypass guard or use different cycle
    # Guard allowed transitions: OBSERVE -> [RETRIEVE, PLAN, ERROR]
    # So OBSERVE -> OBSERVE will actually raise RuntimeError in Guard first!
    # We should test a valid cycle that loops infinitely, e.g.
    # OBSERVE -> RETRIEVE -> PLAN -> DECIDE -> ERROR -> IDLE is standard.
    # Let's try OBSERVE -> RETRIEVE -> PLAN -> ERROR -> IDLE (Wait, ERROR -> IDLE is exit)
    
    # We need a cycle that doesn't hit IDLE.
    # Guard allows:
    # ACT -> REFLECT -> MEMORY_WRITE -> IDLE
    # Maybe we can mock the guard allowed transitions? 
    # Or just use an allowed cycle?
    # But FSM loop logic is: "while current_state != State.IDLE"
    
    # Let's patch StateGuard to allow OBSERVE -> OBSERVE for this test?
    # No, better to test with "MAX_TRANSITIONS" limit.
    
    # Let's set MAX_TRANSITIONS to a small number, e.g., 3.
    # And have a cycle: OBSERVE -> RETRIEVE -> PLAN -> OBSERVE (if allowed?)
    # Guard logic is strict.
    
    # Actually, let's just mock the handler to return State.IDLE after N calls, 
    # but verify that if it takes too many, it stops.
    
    # Wait, the failure mode is "FSM Loop Limit Exceeded".
    # I can use a mocked StateGuard that allows everything?
    # Or I can just patch `_allowed_transitions`.
    
    # Let's patch `StateGuard._allowed_transitions` safely
    with patch.dict(guard._allowed_transitions, {State.OBSERVE: [State.OBSERVE, State.ERROR]}):
        
        # Now OBSERVE->OBSERVE is valid in Guard.
        async def looping_handler(context):
            return State.OBSERVE
            
        fsm.register_handler(State.OBSERVE, AsyncMock(execute=looping_handler))
        
        # Set limit to 5
        with patch('core.fsm.MAX_TRANSITIONS', 5):
             result = await fsm.process_event({
                 "user_id": user_id,
                 "type": "message",
                 "text": "Loop me"
             })
             
             # Check if we hit the error
             assert "FSM Loop Limit Exceeded" in result.errors
             # Should end in ERROR or IDLE (if ERROR handler leads to IDLE)
             # Our setup_fsm makes ERROR -> IDLE.
             # So safely finishes.

@pytest.mark.asyncio
async def test_timeout_trap():
    """
    Test that FSM execution times out if handlers take too long.
    """
    user_id = 222
    
    # Mock handler that sleeps longer than timeout
    async def slow_handler(context):
        await asyncio.sleep(0.2) # Sleep 0.2s
        return State.IDLE
        
    fsm.register_handler(State.OBSERVE, AsyncMock(execute=slow_handler))
    
    # Set timeout to 0.1s
    with patch('core.fsm.FSM_TIMEOUT_SECONDS', 0.1):
        # We need to ensure asyncio.timeout uses the patched value.
        # Since it is imported as constant in the function, patching core.fsm.FSM_TIMEOUT_SECONDS 
        # SHOULD work if the function reads it at runtime. 
        # (It does, because it's global scope lookup).
        
        # Note: asyncio.timeout(FSM_TIMEOUT_SECONDS) uses the value at call time.
        
        result = await fsm.process_event({
            "user_id": user_id,
            "type": "message",
            "text": "Slow poke"
        })
        
        assert "Processing timed out" in result.errors
