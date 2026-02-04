# 🛠️ ENGINEERING GUIDE: TASK-012 (Active Reflection)

## 🎯 Context
We are implementing the **Active Reflection Loop**. The bot will evaluate its own performance after each interaction and store "lessons" to improve future responses.

## 🧱 Work Zones

### 1. Database Schema (`data/bot_data.db`)
- **Action**: Create table `lessons_learned`.
- **Columns**:
  - `id` (INTEGER PK)
  - `user_id` (INTEGER)
  - `interaction_id` (TEXT)
  - `score` (INTEGER, 1-10)
  - `critique` (TEXT)
  - `correction` (TEXT) - What to do differently next time.
  - `created_at` (TIMESTAMP)

### 2. `core/llm_service.py`
- **Action**: Add `evaluate_performance(user_input, bot_response)` function.
- **Model**: Use `MODEL_FAST` (Gemini Flash) for speed/cost.
- **Prompt**:
  > "Evaluate this AI response. Did it answer the user's intent? Was the tone correct?
  > Output JSON: {score: int, critique: str, correction: str}"

### 3. `states/reflect.py`
- **Logic**:
  - Call `evaluate_performance`.
  - If `score < 7`:
    - Log "⚠️ Low Performance detected".
    - Insert into `lessons_learned`.
  - If `score >= 7`:
    - Log "✅ Good cycle".

### 4. `states/plan.py`
- **Logic**:
  - Before generating response, fetch last 3 records from `lessons_learned` for this user.
  - Inject into System Prompt:
    > "CRITICAL LEARNINGS FROM PAST MISTAKES:
    > 1. [Correction 1]
    > 2. [Correction 2]
    > AVOID THESE ERRORS."

## 🧪 Verification Plan
1.  **Bad Interaction**: Force a bad response (or simulate one).
2.  **Check DB**: Verify `lessons_learned` has a new row.
3.  **Next Turn**: Verify the `PLAN` state logs show "Injecting 1 lessons".

## 📜 Coder Prompt Rules
- **Rule 1**: Efficiency. Do not run reflection on trivial "Hello" messages.
- **Rule 2**: Privacy. Lessons are per-user.
