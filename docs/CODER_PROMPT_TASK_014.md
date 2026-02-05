# 🛠️ ENGINEERING GUIDE: TASK-014 (Kernel Hardening)

## 🎯 Objective
Implement "Clean Kernel" observability features: Trace IDs, Centralized JSON Logging, and Critical Alerting.

## 🧱 Work Zones

### 1. Context Tracing (`core/context.py`)
- **Action**: Add `trace_id` field to `ExecutionContext`.
- **Logic**: 
  - Initialize with `str(uuid.uuid4())`.
  - Ensure it propagates if context is rebuilt (though usually context is fresh per event).

### 2. Centralized Logging (`core/logger.py`)
- **Action**: Create new module.
- **Logic**:
  - Class `JSONFormatter(logging.Formatter)`:
    - Override `format(record)`.
    - Output keys: `timestamp` (ISO8601), `level`, `trace_id` (extract from record or context), `message`, `module`, `line`.
  - Function `setup_logging(log_file: str, level: str)`:
    - Configure root logger.
    - Add `RotatingFileHandler` (10MB max, backup 5) pointing to `log_file`.
    - Set formatter to `JSONFormatter`.
    - Also keep `StreamHandler` for console (simple format).

### 3. FSM Integration (`main.py`)
- **Action**: Call `core.logger.setup_logging` at startup.
- **Param**: Log to `logs/delio_trace.json`.

### 4. Admin Notify (`core/state_guard.py`)
- **Action**: 
  - Add `set_bot(bot_instance)` to `StateGuard`.
  - Update `main.py` to call `guard.set_bot(bot)` after initialization.
- **Logic**:
  - In `StateGuard.enter` and `assert_allowed` `except` blocks:
    - If `bot` is set:
      - `await bot.send_message(config.ADMIN_IDS[0], f"🚨 CRITICAL GUARD FAILURE:\n{type(e).__name__}: {str(e)}\nUser: {user_id}")`
    - Wrap this in a safe try/except so alerting doesn't crash the crash handler.

## 🧪 Verification Plan
1.  **Trace Check**: Send "Hello". Check `logs/delio_trace.json`. Verify `trace_id` exists.
2.  **Alert Check**: 
    - Temporarily add `raise RuntimeError("Test Crash")` in `StateGuard.enter`.
    - Trigger state change.
    - Verify Telegram message received.

## 📜 Coding Rules
1.  **No Blocking**: Alerting must be fire-and-forget (async).
2.  **JSON Schema**: Ensure `message` field is a string, not an object, to avoid parsing issues in log viewers later.
