# TASK-005: Conditional Routing in PLAN State (Implementation Plan)

## 🚨 Проблема
Зараз `PlanState` завжди повертає `State.DECIDE`, навіть якщо:
- Actor (Gemini) повернув порожній рядок.
- Critic (DeepSeek) забракував відповідь як небезпечну/некоректну.
- Сталася помилка API, яку ми "проковтнули" (silent fail).

Це призводить до того, що користувач іноді отримує порожні повідомлення або повідомлення про помилку в форматі звичайної відповіді.

## 🛠️ Запропоновані Зміни

### 1. [MODIFY] `states/plan.py`
Змінити логіку повернення стану (return logic) в кінці методу `execute`.

```python
    async def execute(self, context: ExecutionContext) -> State:
        # ... (execution of Actor & Critic) ...
        
        # --- NEW ROUTING LOGIC ---
        
        # 1. Check for Critical Errors flagged by Critic
        synergy_label = context.metadata.get("model_used", "")
        if "⚠️" in synergy_label:
            logger.warning(f"⛔ Plan Rejected by Critic. User: {context.user_id}")
            context.errors.append("Critic rejected the response (Potential Safety/Logic Issue)")
            return State.ERROR
            
        # 2. Check for Degenerate/Empty Response
        if not context.response or len(context.response.strip()) < 5:
            logger.warning(f"⛔ Plan Empty. User: {context.user_id}")
            context.errors.append("Actor produced empty response")
            return State.ERROR
            
        # 3. Check for 'Hallucinated' Error Messages
        # Sometimes LLMs print "I cannot do that" as text. We might want to catch standard refuses.
        # (Optional, maybe for later)

        # Success path
        return State.DECIDE
```

### 2. Забезпечити обробку в `ERROR` state
Переконатися, що `State.ERROR` вміє коректно "вибачитися" перед користувачем, якщо ми туди потрапили з `PLAN`.

*(Це зазвичай вже є в `states/error.py`, але варто перевірити)*.

## 🧪 Verification Plan

### Test Case 1: Empty Response
1. Замокати Actor так, щоб він повернув `""` (пусту строку).
2. Запустити потік.
3. Очікувати перехід в `State.ERROR`.

### Test Case 2: Critic Rejection
1. Замокати Critic так, щоб він повернув лейбл `"♊⚠️"`.
2. Запустити потік.
3. Очікувати перехід в `State.ERROR` та запис в `context.errors`.

## ✅ Acceptance Criteria
- [ ] Якщо `context.response` порожній -> йдемо в `ERROR`.
- [ ] Якщо Critic повернув статус помилки -> йдемо в `ERROR`.
- [ ] Успішна відповідь -> йдемо в `DECIDE`.
