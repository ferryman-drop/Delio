# 🛠️ ENGINEERING GUIDE: TASK-010 Implementation

## 🎯 Context
We are implementing the **Proactive Heartbeat** mechanism. The bot currently "sleeps" between user messages. We want it to wake up periodically, check the user's data (schedule/goals), and decide if it should send a spontaneous message (Notification) or stay silent (SKIP).

## 🧱 Work Zones

### 1. `scheduler.py` (The Trigger)
- **Goal**: Trigger the FSM for *each* active user, not just system user 0.
- **Action**: 
  - In `trigger_heartbeat`, fetch unique user IDs from `data/chat_history.db`.
  - Filter out users who are "busy" (StateGuard not IDLE).
  - Call `fsm.process_event` with `type="heartbeat"` for each user.

### 2. `states/plan.py` (The Brain)
- **Goal**: Handle `event_type='heartbeat'`.
- **Logic**:
  - If event is heartbeat, inject a special System Instruction:
    > "CONTEXT: Routine Heartbeat Check.
    > TASK: Review user's context (time, goals, recent history).
    > DECISION: If there is something CRITICAL/USEFUL to say (reminder, insight, support), generate it.
    > IF NOT: Output 'SKIP'."

### 3. `states/decide.py` (The Filter)
- **Goal**: Handle 'SKIP'.
- **Logic**:
  - If Actor response == "SKIP" (or close to it):
    - Log "Heartbeat skipped for user X".
    - Transition to `State.IDLE`.
  - Else:
    - Transition to `State.RESPOND` (to send the message).

### 4. `config.py`
- **Tweak**: Ensure `HEARTBEAT_INTERVAL` is set (default 30 min).

## 🧪 Verification Plan
1.  **Manual Trigger**: Expose a temporary command or script to force-run `trigger_heartbeat`.
2.  **Test Case A (Quiet)**: Run heartbeat. Expect log: "Heartbeat skipped".
3.  **Test Case B (Active)**: Add a fake "Urgent Note" to user memory. Run heartbeat. Expect bot message: "Нагадую про..."

## 📜 Coder Prompt Rules
- **Rule 1**: Do NOT spam the user. The default bias should be SILENCE.
- **Rule 2**: Use `logger.info` heavily to debug the heartbeat loop.
