# 🛠️ FINAL HOTFIX: Vision Delivery & Error Handling

## 🎯 Objective
Fix the "silent failure" where Vision responses are blocked by Timeout markers and the lack of an Error handler.

## 🧱 Work Zones

### 1. Planning Logic (`states/plan.py`)
- **Problem**: The system treats `(Timeout)` as a critical safety rejection because it contains the `⚠️` emoji.
- **Action**: Update the routing check.
- **Code Logic**:
```python
synergy_label = context.metadata.get("model_used", "")
# Route to ERROR only if it's a REAL rejection/error, NOT a simple API timeout
if "⚠️" in synergy_label and "(Timeout)" not in synergy_label:
    logger.warning(f"⛔ Plan Rejected by Critic. User: {context.user_id}")
    return State.ERROR
```

### 2. FSM Registration (`main.py`)
- **Problem**: `ErrorState` is imported but NOT registered in the FSM, causing `❌ No handler for state: State.ERROR`.
- **Action**: Register the handler.
- **Code Logic**:
```python
from states.error import ErrorState
# ...
fsm.register_handler(State.ERROR, ErrorState(bot))
```

### 3. Respond Style (`handlers.py`)
- **Action**: Ensure `handle_photo` uses a single clean message.
- **Current**: `await message.answer(f"👀 Дивлюся... (Caption: {caption})")`
- **Recommended**: `await message.answer("📸 *Аналізую зображення...*")`

## 🧪 Verification
1.  Upload the Polopiryna photo.
2.  **Expected**: Even if DeepSeek times out (15s), the Gemini response should reach the user.
3.  **Expected**: If a real error occurrs, the user gets a "⚠️ Внутрішня помилка" message instead of silence.
