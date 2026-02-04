# TASK-001: Per-User FSM Concurrency Lock

## Проблема

Поточна реалізація `StateGuard` НЕ є thread-safe для конкурентних async викликів від одного користувача.

### Сценарій збою
```python
# User 123 надсилає два повідомлення майже одночасно
Task 1: fsm.process_event({"user_id": 123, "text": "Привіт"})
Task 2: fsm.process_event({"user_id": 123, "text": "Як справи?"})

# Race condition в StateGuard._user_states
Task 1: reads _user_states[123] = IDLE
Task 2: reads _user_states[123] = IDLE    ❌ ОБИДВА БАЧАТЬ IDLE
Task 1: writes _user_states[123] = OBSERVE
Task 2: writes _user_states[123] = OBSERVE ❌ ПЕРЕЗАПИСАВ
Task 1: transitions OBSERVE → RETRIEVE
Task 2: tries OBSERVE → RETRIEVE          ❌ ДУБЛІКАТ ПОТОКУ
```

**Результат**: Контекст корумпований, дві відповіді для одного запиту.

---

## User Review Required

> [!IMPORTANT]
> **Breaking Change Potential**: Додавання locks може змінити behavior у edge cases де раніше race conditions проходили "успішно" (хоча й некоректно).

> [!WARNING]  
> **Performance Impact**: Кожен перехід стану тепер чекатиме на lock. Оцінка: +1-5мс латентності на користувача.

> [!CAUTION]
> **Deadlock Risk**: Якщо інший код теж використовує locks і захоплює їх у зворотному порядку, можливий deadlock. Потрібен timeout механізм.

---

## Proposed Changes

### Core Module

#### [MODIFY] [state_guard.py](file:///root/ai_assistant/core/state_guard.py)

**Зміна 1: Додати lock storage**

Додати в `StateGuard.__init__()`:
```python
from typing import Dict
import asyncio

class StateGuard:
    def __init__(self):
        self._user_states = {}  # user_id → State
        self._user_locks: Dict[int, asyncio.Lock] = {}  # NEW
        self._lock_acquisition_lock = asyncio.Lock()    # NEW: meta-lock
```

**Обґрунтування**:
- `_user_locks` — мапінг user_id на його персональний Lock
- `_lock_acquisition_lock` — meta-lock для thread-safe створення нових user locks

---

**Зміна 2: Додати helper для отримання lock**

Нова приватна функція:
```python
async def _get_lock(self, user_id: int) -> asyncio.Lock:
    """
    Thread-safe отримання або створення lock для користувача.
    Використовує meta-lock для запобігання race condition при створенні locks.
    """
    # Fast path: lock вже існує
    if user_id in self._user_locks:
        return self._user_locks[user_id]
    
    # Slow path: потрібно створити новий lock
    async with self._lock_acquisition_lock:
        # Double-check pattern (інший task міг створити між перевіркою і lock)
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]
```

**Обґрунтування**:
- Double-check locking pattern для продуктивності
- Meta-lock запобігає створенню кількох locks для одного user_id
- Fast path без lock для вже існуючих користувачів

---

**Зміна 3: Захистити StateGuard.enter()**

Обгорнути критичну секцію в lock:
```python
async def enter(self, user_id: int, next_state: State):
    """
    Attempt to transition to a new state for a specific user.
    NOW THREAD-SAFE: Uses per-user lock.
    """
    user_lock = await self._get_lock(user_id)
    
    try:
        async with asyncio.timeout(60):  # 60-second timeout
            async with user_lock:
                current_state = self.get_state(user_id)

                # ANY state can transition to ERROR
                if next_state == State.ERROR:
                    logger.warning(f"⚠️ Emergency transition to ERROR for {user_id} from {current_state}")
                    self._user_states[user_id] = next_state
                    return

                allowed = self._allowed_transitions.get(current_state, [])
                if next_state not in allowed:
                    msg = f"❌ FORBIDDEN TRANSITION for {user_id}: {current_state.name} → {next_state.name}"
                    logger.error(msg)
                    self._user_states[user_id] = State.ERROR
                    raise RuntimeError(msg)

                logger.debug(f"➡️ StateGuard [{user_id}]: {current_state.name} → {next_state.name}")
                self._user_states[user_id] = next_state
                
    except asyncio.TimeoutError:
        logger.critical(f"🔒 DEADLOCK DETECTED for user {user_id}! Lock timeout after 60s")
        # Force ERROR state even without lock (emergency escape)
        self._user_states[user_id] = State.ERROR
        raise RuntimeError(f"State transition deadlock for user {user_id}")
```

**Обґрунтування**:
- Lock захоплюється ПЕРЕД читанням `current_state`
- Timeout 60 секунд запобігає deadlock (нормальна транзакція < 1 секунда)
- Emergency escape: якщо timeout, force ERROR без lock

---

**Зміна 4: Захистити StateGuard.assert_allowed()**

```python
async def assert_allowed(self, user_id: int, action: Action):
    """
    Verify if an action is allowed in the user's current state.
    NOW THREAD-SAFE: Uses per-user lock.
    """
    user_lock = await self._get_lock(user_id)
    
    async with user_lock:
        current_state = self.get_state(user_id)
        allowed_states = self._side_effect_matrix.get(action, [])
        if current_state not in allowed_states:
            msg = f"🛡️ STATE GUARD BLOCK [{user_id}]: Action {action.name} is FORBIDDEN in {current_state.name}"
            logger.critical(msg)
            raise PermissionError(msg)
```

**Обґрунтування**:
- Читання `current_state` повинно бути атомарним з перевіркою
- Без lock, `current_state` може змінитися між get та check

---

**Зміна 5: Cleanup метод для звільнення locks**

Нова публічна функція:
```python
def cleanup_user_lock(self, user_id: int):
    """
    Видалити lock користувача після force_idle().
    Викликається після завершення FSM потоку для звільнення пам'яті.
    """
    if user_id in self._user_locks:
        del self._user_locks[user_id]
        logger.debug(f"🧹 Cleaned up lock for user {user_id}")
```

**Використання**:
У [`core/fsm.py:60-61`](file:///root/ai_assistant/core/fsm.py#L60-L61) після `guard.force_idle(user_id)`:
```python
finally:
    guard.force_idle(user_id)
    guard.cleanup_user_lock(user_id)  # NEW
```

---

### FSM Controller

#### [MODIFY] [fsm.py](file:///root/ai_assistant/core/fsm.py)

**Зміна 1: Оновити обробку помилок**

У блоці `finally` (рядок 60-61):
```python
finally:
    guard.force_idle(user_id)
    guard.cleanup_user_lock(user_id)  # NEW: звільнити lock після завершення
```

**Обґрунтування**: Запобігає memory leak від накопичення locks

---

## Verification Plan

### Automated Tests

#### Test 1: Concurrent Same-User Messages
```python
# tests/test_task_001_concurrency.py

import asyncio
import pytest
from core.fsm import instance as fsm
from core.state_guard import guard

@pytest.mark.asyncio
async def test_concurrent_messages_same_user():
    """
    Два конкурентні повідомлення від user_id=999 не повинні race.
    """
    user_id = 999
    
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
    assert guard.get_state(user_id) == State.IDLE  # Повернулось в IDLE
```

#### Test 2: Different Users Parallel
```python
@pytest.mark.asyncio
async def test_different_users_parallel():
    """
    Повідомлення від різних користувачів повинні обробляться паралельно.
    """
    import time
    
    async def send_slow_message(user_id):
        start = time.time()
        await fsm.process_event({
            "user_id": user_id,
            "type": "message",
            "text": "Test"
        })
        return time.time() - start
    
    # Запустити 3 користувачів паралельно
    times = await asyncio.gather(
        send_slow_message(101),
        send_slow_message(102),
        send_slow_message(103)
    )
    
    # Якщо паралельні, сумарний час < (час одного * 3)
    total_time = sum(times)
    max_sequential_time = max(times) * 3
    
    assert total_time < max_sequential_time * 0.5  # At least 2x speedup
```

#### Test 3: Deadlock Detection
```python
@pytest.mark.asyncio
async def test_lock_timeout_prevents_deadlock():
    """
    Якщо state handler зависає, timeout повинен спрацювати.
    """
    from unittest.mock import patch
    from core.state import State
    
    user_id = 888
    
    # Mock handler that hangs
    async def hanging_handler(context):
        await asyncio.sleep(120)  # Зависнути на 2 хвилини
        return State.IDLE
    
    with patch.object(fsm.state_handlers[State.OBSERVE], 'execute', hanging_handler):
        with pytest.raises(RuntimeError, match="deadlock"):
            await fsm.process_event({
                "user_id": user_id,
                "type": "message",
                "text": "Test"
            })
    
    # Після timeout, user повинен бути в ERROR
    assert guard.get_state(user_id) == State.ERROR
```

#### Test 4: Lock Cleanup
```python
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
```

---

### Manual Verification

1. **Load Testing**:
   - Запустити 10 користувачів, кожен надсилає 100 повідомлень
   - Перевірити logs на race conditions
   - Виміряти latency overhead

2. **Backward Compatibility**:
   - Запустити всі існуючі тести: `pytest tests/`
   - Перевірити що жоден не падає

3. **Performance Benchmark**:
   ```bash
   # До змін
   time python -m pytest tests/test_fsm.py -v
   
   # Після змін
   time python -m pytest tests/test_fsm.py -v
   
   # Різниця повинна бути < 10%
   ```

---

## Rollback Strategy

### Immediate Rollback (якщо щось не так)

**Крок 1**: Видалити всі locks з `StateGuard`:
```python
# В state_guard.py, повернути до:
class StateGuard:
    def __init__(self):
        self._user_states = {}
        # ВИДАЛИТИ: self._user_locks, self._lock_acquisition_lock
```

**Крок 2**: Видалити `async with` блоки:
```python
# В enter() та assert_allowed(), видалити:
# async with user_lock:
```

**Крок 3**: Видалити cleanup виклик:
```python
# В fsm.py finally block:
guard.force_idle(user_id)
# ВИДАЛИТИ: guard.cleanup_user_lock(user_id)
```

**Крок 4**: Запустити тести:
```bash
pytest tests/ -v
```

**Час відкату**: ~5 хвилин (якщо є git diff)

---

### Feature Flag Alternative

Додати конфігураційний прапорець:
```python
# config.py
ENABLE_FSM_LOCKS = os.getenv("ENABLE_FSM_LOCKS", "true").lower() == "true"
```

У `StateGuard.enter()`:
```python
if config.ENABLE_FSM_LOCKS:
    async with user_lock:
        # ... locked logic
else:
    # ... original logic without locks
```

**Переваги**: Можна вимкнути locks без зміни коду  
**Недоліки**: Додатковий код для підтримки

---

## Acceptance Criteria

✅ **AC-1**: Два одночасні виклики `fsm.process_event(user_id=X)` виконуються **послідовно**  
✅ **AC-2**: Виклики для **різних** user_id виконуються **паралельно**  
✅ **AC-3**: Всі існуючі FSM тести **проходять** без змін  
✅ **AC-4**: Timeout на lock ≤ 60 секунд, після чого `RuntimeError`  
✅ **AC-5**: Latency overhead < 5мс на lock acquisition  
✅ **AC-6**: Memory leak відсутній (locks звільняються після `force_idle`)  
✅ **AC-7**: Код пройшов code review та має docstrings

---

## Estimated Effort

| Фаза | Час |
|------|-----|
| Модифікація `state_guard.py` | 2 год |
| Модифікація `fsm.py` | 30 хв |
| Написання тестів | 1 год |
| Debugging та edge cases | 30 хв |
| **Всього** | **4 години** |

---

## Next Steps

1. ✅ Переглянути цей план
2. ⏳ Дочекатися approve від користувача
3. ⏳ Реалізувати зміни
4. ⏳ Запустити automated tests
5. ⏳ Виконати manual verification
6. ⏳ Merge до main branch
