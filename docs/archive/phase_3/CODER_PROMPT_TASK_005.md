# 🛠️ ENGINEERING GUIDE: TASK-005 Implementation

## 🎯 Context
The FSM's `PLAN` state blindly transitions to `DECIDE` even if the Actor (Gemini) generates an empty response or the Critic (DeepSeek) rejects the plan. This results in "silent failures" or broken UX.

## 🧱 Work Zone
1.  **`states/plan.py`**: Modify the return logic in `execute()`.
2.  **`states/error.py`**: Verify it can handle errors coming from PLAN (it likely does, just check).

## 📜 Coder Prompt Rules (Instructions for Implementation)

### 1. The Logic
Currently, `PlanState.execute` ends with:
```python
return State.DECIDE
```

You need to change it to something like:
```python
if critical_error or empty_response:
    return State.ERROR
return State.DECIDE
```

### 2. Detection Criteria
- **Critic Rejection**: Check `context.metadata.get("model_used")`. If it contains `"⚠️"` (or whatever marker `Critic` uses), it's a rejection.
- **Empty Response**: Check if `context.response` is empty or just whitespace.

### 3. Error Handling
- If rejecting, append a clear message to `context.errors`.
- Example: `context.errors.append("Critic rejected response for safety")`

## 🧪 Verification
- **Test Case**: Mock `llm.generate` to return `""`.
## ✅ Статус Реалізації (Implementation Status) - Виконано ✅
1. **`states/plan.py`**:
   - Реалізовано перевірку на порожню відповідь від LLM.
   - Реалізовано перевірку на критичну помилку від Critic ("⚠️" маркер).
   - У разі помилки стан переходить у `State.ERROR`.
2. **`states/error.py`**:
   - Стан коректно обробляє помилки та повідомляє користувача.
   - Спеціальна обробка повідомлень "Critic rejected".
3. **Tests**:
   - `tests/test_plan_failure.py` підтвердив правильну поведінку при емуляції збоїв.

### Змінені файли:
- `states/plan.py`
