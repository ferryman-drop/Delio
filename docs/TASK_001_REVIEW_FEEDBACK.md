# 📋 REVIEW-001: Per-User FSM Concurrency Lock Implementation

**Date**: 2026-02-03  
**Reviewer**: The Critic (Code Review & QA)  
**Status**: ❌ **REJECT — CHANGES REQUESTED**

---

## ⚖️ DECISION

**[REJECT - CHANGES REQUESTED]**

**Загальна оцінка**: 6.5/10  
**Spec Alignment**: 6/10  
**AC Passed**: 3/7 ✅ | 2/7 ❌ | 2/7 ⚠️

---

## 1. Spec Alignment & Constraints

| Критерій | Результат | Деталі |
|----------|-----------|---------|
| **Objective met** | ⚠️ **Частково** | Основний функціонал реалізовано, але є критичні пропуски |
| **Scope strictly followed** | ❌ **НІ** | Кодер НЕ оновив файл `scripts/verify_kernel.py`, який є **поза межами** зазначеного скоупа |
| **Constraints respected** | ✅ **ТАК** | Не торкнувся `main.py`, не порушив FSM boundaries |

---

## 2. ⛔ CRITICAL FINDINGS (MUST FIX — BLOCKING APPROVAL)

### 🚨 **CRITICAL-1: Порушення скоупа — Неоновлений legacy код**

**Файл**: `scripts/verify_kernel.py`  
**Рядки**: 70, 72, 80

**Проблема**:
```python
# РЯДОК 70 ❌
guard.enter(State.OBSERVE)  # Немає await! Немає user_id!

# РЯДОК 72 ❌
guard.assert_allowed(Action.LLM_CALL)  # Немає await! Немає user_id!

# РЯДОК 80 ❌
guard.enter(State.ACT)  # Немає await! Немає user_id!
```

**Вплив**:
- При запуску верифікаційного скрипта система **ПАДАТИМЕ** з `TypeError`
- Це Breaking Change, який **НЕ БУВ** зафіксований в Implementation Output
- `verify_kernel.py` НЕ був згаданий у списку модифікованих файлів

**🔧 FIX REQUIRED**:
```python
# scripts/verify_kernel.py

async def test_state_guard_blocking():
    print("\n--- 🛡️ TEST 2: State Guard Enforcement ---")
    user_id = 999  # Mock user for testing
    guard.force_idle(user_id)
    
    # Test 2.1: Action out of state
    try:
        await guard.enter(user_id, State.OBSERVE)
        print("Current State: OBSERVE. Attempting LLM call (should fail)...")
        await guard.assert_allowed(user_id, Action.LLM_CALL)
        print("🔴 FAILURE: Guard allowed LLM call in OBSERVE.")
    except PermissionError as e:
        print(f"✅ SUCCESS: Guard blocked action: {e}")

    # Test 2.2: Illegal transition
    try:
        print("Attempting Illegal Transition: OBSERVE -> ACT (skipping PLAN/DECIDE)...")
        await guard.enter(user_id, State.ACT)
        print("🔴 FAILURE: Guard allowed OBSERVE -> ACT.")
    except RuntimeError as e:
        print(f"✅ SUCCESS: Guard blocked transition: {e}")
        
    guard.force_idle(user_id)
```

---

### 🚨 **CRITICAL-2: Race condition у deadlock escape**

**Файл**: `core/state_guard.py`  
**Рядки**: 97-101

**Проблема**:
```python
except asyncio.TimeoutError:
    logger.critical(f"🔒 DEADLOCK DETECTED for user {user_id}! Lock timeout after 60s")
    # Force ERROR state even without lock (emergency escape)
    self._user_states[user_id] = State.ERROR  # ❌ RACE CONDITION!
    raise RuntimeError(f"State transition deadlock for user {user_id}")
```

**Аналіз**:
- Після timeout lock НЕ звільнений
- Запис `self._user_states[user_id] = State.ERROR` відбувається **БЕЗ LOCK** → race condition!
- Якщо інший task теж чекає на lock, він може одночасно писати в `_user_states[user_id]`

**🔧 FIX REQUIRED**:
```python
except asyncio.TimeoutError:
    logger.critical(f"🔒 DEADLOCK DETECTED for user {user_id}! Lock timeout after 60s")
    # НЕ змінювати state тут — це небезпечно
    # FSM.process_event має finally block, який зробить force_idle()
    raise RuntimeError(f"State transition deadlock for user {user_id}")
```

---

### 🚨 **CRITICAL-3: Timeout застосований неправильно**

**Файл**: `core/state_guard.py`  
**Рядок**: 77

**Проблема**:
```python
async with asyncio.timeout(60):  # 60-second timeout
    async with user_lock:
        # ... critical section
```

**Аналіз**:
- Timeout застосовано до **ВСІЄЇ** критичної секції
- Якщо логіка state mutation займе довше ніж залишок від 60 секунд → timeout **ПОСЕРЕДИНІ** критичної секції → **PARTIAL MUTATION**

**🔧 FIX REQUIRED**:
```python
async def enter(self, user_id: int, next_state: State):
    """
    Attempt to transition to a new state for a specific user.
    NOW THREAD-SAFE: Uses per-user lock with timeout on acquisition only.
    """
    user_lock = await self._get_lock(user_id)
    
    try:
        # Timeout ТІЛЬКИ на lock acquisition
        async with asyncio.timeout(60):
            await user_lock.acquire()
        
        try:
            # State mutation logic БЕЗ timeout — має завершитися завжди
            current_state = self.get_state(user_id)

            # ANY state can transition to ERROR
            if next_state == State.ERROR:
                logger.warning(f"⚠️ Emergency transition to ERROR for {user_id} from {current_state}")
                self._user_states[user_id] = next_state
                return

            allowed = self._allowed_transitions.get(current_state, [])
            if next_state not in allowed:
                msg = f"❌ FORBIDDEN TRANSITION for {user_id}: {current_state.name} -> {next_state.name}"
                logger.error(msg)
                self._user_states[user_id] = State.ERROR
                raise RuntimeError(msg)

            logger.debug(f"➡️ StateGuard [{user_id}]: {current_state.name} -> {next_state.name}")
            self._user_states[user_id] = next_state
        finally:
            user_lock.release()
            
    except asyncio.TimeoutError:
        logger.critical(f"🔒 DEADLOCK DETECTED for user {user_id}! Lock acquisition timeout after 60s")
        raise RuntimeError(f"Lock acquisition timeout for user {user_id}")
```

**АНАЛОГІЧНО** виправити `assert_allowed()`:
```python
async def assert_allowed(self, user_id: int, action: Action):
    """
    Verify if an action is allowed in the user's current state.
    NOW THREAD-SAFE: Uses per-user lock with timeout on acquisition only.
    """
    user_lock = await self._get_lock(user_id)
    
    try:
        async with asyncio.timeout(60):
            await user_lock.acquire()
        
        try:
            current_state = self.get_state(user_id)
            allowed_states = self._side_effect_matrix.get(action, [])
            if current_state not in allowed_states:
                msg = f"🛡️ STATE GUARD BLOCK [{user_id}]: Action {action.name} is FORBIDDEN in {current_state.name}"
                logger.critical(msg)
                raise PermissionError(msg)
        finally:
            user_lock.release()
            
    except asyncio.TimeoutError:
        logger.critical(f"🔒 Lock acquisition timeout for user {user_id}")
        raise RuntimeError(f"Lock acquisition timeout for user {user_id}")
```

---

### 🚨 **CRITICAL-4: Неповний grep-пошук викликів**

**Проблема**: Кодер НЕ виконав повний пошук всіх викликів `guard.enter()` та `guard.assert_allowed()` по кодбейзі

**🔧 ACTION REQUIRED**:
```bash
# Виконати пошук
grep -r "guard\.enter\|guard\.assert_allowed" /root/ai_assistant --include="*.py"

# Перевірити кожен файл
# Переконатися що ВСІ виклики мають:
# 1. await keyword
# 2. user_id parameter
# 3. Функція є async def
```

**Виявлені файли**:
- ✅ `core/fsm.py` — ОНОВЛЕНО
- ✅ `tools.py` — ОНОВЛЕНО
- ✅ `states/memory_write.py` — ОНОВЛЕНО
- ✅ `states/respond.py` — ОНОВЛЕНО
- ✅ `core/memory/funnel.py` — ОНОВЛЕНО
- ✅ `legacy/old_core.py` — ОНОВЛЕНО
- ❌ **`scripts/verify_kernel.py`** — **НЕ ОНОВЛЕНО** ← FIX THIS!

---

## 3. 🟡 MINOR ISSUES (Should Fix)

### MINOR-1: Відсутність timeout конфігурації

**Рекомендація**:
```python
# config.py
STATE_TRANSITION_TIMEOUT = int(os.getenv("STATE_TRANSITION_TIMEOUT", "60"))

# state_guard.py
import config
async with asyncio.timeout(config.STATE_TRANSITION_TIMEOUT):
```

---

### MINOR-2: Test Coverage недостатня для edge cases

**Файл**: `tests/test_task_001_concurrency.py`

**Додати тести**:
1. **Concurrent lock cleanup** (два task викликають `cleanup_user_lock()` одночасно)
2. **Exception до finally блоку** (якщо `process_event` падає раніше)

---

### MINOR-3: Логування недостатнє для debugging

**Рекомендація**:
```python
async def _get_lock(self, user_id: int) -> asyncio.Lock:
    # Fast path: lock вже існує
    if user_id in self._user_locks:
        logger.debug(f"🔓 Lock retrieved (fast path) for user {user_id}")
        return self._user_locks[user_id]
    
    # Slow path: потрібно створити новий lock
    async with self._lock_acquisition_lock:
        if user_id not in self._user_locks:
            logger.debug(f"🔒 Creating new lock for user {user_id}")
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]
```

---

## 4. 🛡️ Security Note

**⚠️ ПОТЕНЦІЙНА DoS ВРАЗЛИВІСТЬ**:
- Зловмисник може надіслати 1000 повідомлень → створити 1000 locks → memory exhaustion

**Рекомендація** (optional, але бажано):
```python
# state_guard.py
MAX_CONCURRENT_USERS = int(os.getenv("MAX_CONCURRENT_USERS", "500"))

async def _get_lock(self, user_id: int) -> asyncio.Lock:
    if user_id in self._user_locks:
        return self._user_locks[user_id]
    
    async with self._lock_acquisition_lock:
        if user_id not in self._user_locks:
            if len(self._user_locks) >= MAX_CONCURRENT_USERS:
                raise RuntimeError(f"Too many concurrent users ({len(self._user_locks)}). Max: {MAX_CONCURRENT_USERS}")
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]
```

---

## 5. ✅ ACCEPTANCE CRITERIA VERIFICATION

| AC | Опис | Кодер | **Критик** |
|----|------|-------|------------|
| AC-1 | Послідовне виконання для одного user_id | ✅ PASS | ⚠️ **CONDITIONAL** (timeout ризикований) |
| AC-2 | Паралельне виконання для різних user_id | ✅ PASS | ✅ **PASS** |
| AC-3 | Існуючі тести проходять | ✅ PASS | ❌ **FAIL** (`verify_kernel.py` не оновлений) |
| AC-4 | Timeout ≤ 60с з RuntimeError | ✅ PASS | ❌ **FAIL** (race condition на escape) |
| AC-5 | Latency < 5ms | ✅ PASS | ✅ **PASS** |
| AC-6 | Відсутність memory leak | ✅ PASS | ⚠️ **NEEDS VERIFICATION** |
| AC-7 | Code review + docstrings | ✅ PASS | ❌ **FAIL** (в процесі) |

**Результат**: 3/7 PASS, 2/7 FAIL, 2/7 WARNING → **REJECT**

---

## 6. 📋 CHECKLIST FOR CODER (Action Items)

### 🔴 **MUST FIX** (Перед resubmit):

- [ ] **CRITICAL-1**: Оновити `scripts/verify_kernel.py` (додати `await`, `user_id`, зробити async)
- [ ] **CRITICAL-2**: Видалити `self._user_states[user_id] = State.ERROR` з timeout escape
- [ ] **CRITICAL-3**: Перемістити timeout на lock acquisition (не на весь блок)
- [ ] **CRITICAL-4**: Виконати `grep -r` та підтвердити що всі виклики оновлені
- [ ] Запустити `pytest tests/ -v` → має пройти 100%
- [ ] Запустити `python scripts/verify_kernel.py` → не повинен падати
- [ ] Оновити `TASK_001_Implementation_Output.md` з повним списком змінених файлів

### 🟡 **SHOULD FIX** (Бажано):

- [ ] **MINOR-1**: Винести timeout у `config.py`
- [ ] **MINOR-2**: Додати тести для concurrent cleanup
- [ ] **MINOR-3**: Додати debug logging у `_get_lock()`
- [ ] **SECURITY**: Додати `MAX_CONCURRENT_USERS` ліміт

### 🟢 **NICE TO HAVE** (Опціонально):

- [ ] Додати метрики для моніторингу lock wait time
- [ ] Додати memory tracking для `_user_locks` dict size

---

## 7. 🔄 NEXT STEPS

1. ✅ Виправити **ВСІ** CRITICAL-1, CRITICAL-2, CRITICAL-3, CRITICAL-4
2. ✅ Запустити повний test suite
3. ✅ Запустити `verify_kernel.py`
4. ✅ Оновити Implementation Output з повним списком файлів
5. ✅ **Resubmit for re-review**

**Estimated Fix Time**: 1-2 години

---

## 8. 📊 FINAL VERDICT

**Status**: ❌ **REJECT — CHANGES REQUESTED**

**Причини відхилення**:
1. ❌ Критичний legacy код не оновлений → **система зламається**
2. ❌ Race condition у emergency escape → **небезпечно для production**
3. ❌ Timeout застосований неправильно → **ризик partial mutation**

**Коли буде APPROVED**:
- Всі CRITICAL issues виправлені
- Всі тести проходять (включно з `verify_kernel.py`)
- Implementation Output оновлений з повним списком файлів

---

**Reviewer**: The Critic (AGI-lite Kernel)  
**Review Date**: 2026-02-03T21:29:00Z  
**Task Spec**: [TASK_001_Concurrency_Lock_Plan.md](./TASK_001_Concurrency_Lock_Plan.md)  
**Implementation**: [TASK_001_Implementation_Output.md](./TASK_001_Implementation_Output.md)

---

**END OF REVIEW FEEDBACK**
