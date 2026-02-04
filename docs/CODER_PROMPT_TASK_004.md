# 🛠️ ENGINEERING GUIDE: TASK-004 Implementation

## 🎯 Context
The system has a "Side-Channel" leak. `ReminderTool` sends messages directly via `bot_instance.send_message`, bypassing the FSM and `StateGuard`. This causes race conditions.

## 🧱 Work Zone
1.  **`core/tools/reminder_tool.py`**: Modify `_send_notification`.
2.  **`scheduler.py`**: Refactor `trigger_heartbeat` and `bot_instance` usage.
3.  **`core/fsm.py`** & **`core/state_guard.py`**: (Optional) Add support for `SYSTEM_NOTIFICATION` events.

## 📜 Coder Prompt Rules (Instructions for Implementation)

### 1. The "Golden Rule"
**NEVER** use `bot_instance.send_message` directly inside a tool or a scheduler callback. All communication must be an FSM event or wait for an `IDLE` state lock.

### 2. Implementation Methodology
- **Step A**: Update `StateGuard` to include `Action.SYSTEM_NOTIFICATION` allowed in `IDLE` or a new dedicated state `NOTIFY`.
- **Step B**: In `ReminderTool`, instead of `await bot_instance.send_message`, use a wrapper that:
    1. Attempts to acquire the User lock via `StateGuard`.
    2. If successful, proceeds via a controlled FSM transition.
    3. If unsuccessful (User is busy), queues the message or retries after 30s.
- **Step C**: Ensure the message is recorded in the system's Short-Term Memory (Redis/SQLite) so the bot "remembers" it sent the reminder.

### 3. Constraints
- **Scope**: Do not refactor the entire FSM. Only fix the callback mechanism.
- **Safety**: Use `asyncio.Lock` with timeouts to prevent deadlocks between the FSM thread and the Scheduler thread.
- **Performance**: High-frequency heartbeats must not clog the task queue.

## 🧪 Verification
- Run a long-running tool (e.g., `search_tool`) and trigger a 1-minute reminder. 
- **Fail condition**: Reminder text appears in the middle of search results.
- **Success condition**: Reminder waits for search to finish OR is handled by a separate safe concurrency branch.
