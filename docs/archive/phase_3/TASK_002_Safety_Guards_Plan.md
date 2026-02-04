# TASK-002: FSM Loop Safety Guards (Implementation Plan)

## 🚨 Проблема
Поточний цикл FSM (`while current_state != State.IDLE`) не має обмежень. 
- Якщо стан помилково повертає сам себе (`return State.OBSERVE`), бот зациклиться назавжди.
- Якщо обробка займає надто багато часу (завислий запит до API), потік блокується.

## 🛠️ Запропоновані Зміни

### [MODIFY] `core/fsm.py`

#### 1. Додати константи безпеки
У початок файлу:
```python
MAX_TRANSITIONS = 20       # Максимальна глибина "думок"
FSM_TIMEOUT_SECONDS = 30   # Жорсткий ліміт на всю обробку події
```

#### 2. Оновити `FSMController.process_event`
Додати лічильник ітерацій та таймаут на весь процес.

```python
async def process_event(self, event_data: dict):
    # ... (init context) ...
    
    try:
        # Wrap entire process in timeout
        async with asyncio.timeout(FSM_TIMEOUT_SECONDS):
            guard.force_idle(user_id)
            await guard.enter(user_id, State.OBSERVE)
            current_state = State.OBSERVE
            
            transitions_count = 0  # NEW: Counter
            
            while current_state != State.IDLE:
                # NEW: Safety Check
                transitions_count += 1
                if transitions_count > MAX_TRANSITIONS:
                    logger.critical(f"🛑 FSM Loop Limit Exceeded ({MAX_TRANSITIONS}) for user {user_id}")
                    context.errors.append("FSM Loop Limit Exceeded")
                    await guard.enter(user_id, State.ERROR)
                    current_state = State.ERROR
                    # Break loop manually if ERROR handler also fails/loops (optional safety)
                    if transitions_count > MAX_TRANSITIONS + 2:
                        break
                
                # ... (get handler) ...
                # ... (execute handler) ...
                
    except asyncio.TimeoutError:
        logger.critical(f"⏰ FSM Execution Timed Out ({FSM_TIMEOUT_SECONDS}s) for user {user_id}")
        context.errors.append("Processing timed out")
        # Force cleanup via finally block
        
    finally:
        guard.force_idle(user_id)
        guard.cleanup_user_lock(user_id)
```

## 🧪 Verification Plan

### Automated Tests
1. **Infinite Loop Trap**:
   - Створити мок-хендлер для `State.OBSERVE`, який завжди повертає `State.OBSERVE`.
   - Запустити `process_event`.
   - Очікувати: перехід в `State.ERROR` після 20 ітерацій.

2. **Timeout Trap**:
   - Створити мок-хендлер, який робить `await asyncio.sleep(35)`.
   - Запустити `process_event`.
   - Очікувати: `asyncio.TimeoutError` (або оброблений лог) і завершення роботи через 30 сек.

## ✅ Acceptance Criteria
- [ ] Цикл примусово завершується, якщо кількість переходів > 20.
- [ ] Процес примусово завершується, якщо час виконання > 30 сек.
- [ ] У випадку аварійного завершення користувач переводиться в `IDLE` (через finally).
