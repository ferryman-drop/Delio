# Implementation Plan: Power Tools (Phase 3.1)

## Goal
Complete the Autonomous Agent vision by adding Scheduler and File Management capabilities.

## Proposed Changes

### 1. Scheduler Integration: `ReminderTool`
- **File**: `core/tools/reminder_tool.py`
- **Logic**: 
    - Wraps `scheduler.add_job` from `scheduler.py`.
    - Accepts `text` and `time_str` (ISO format or simple delay like "10 minutes").
    - Callback: Sends a message to the user via `bot_instance`.

### 2. File Management: `NoteTool` (Note-taking)
- **File**: `core/tools/note_tool.py`
- **Logic**:
    - Manage files in `data/notes/`.
    - Actions: `write_note(name, content)`, `read_note(name)`, `list_notes()`.
    - Prevents directory traversal (security check).

### 3. FSM Update
- Ensure the `ACT` state can handle these tools. (Already should, as it's generic).

## User Review Required
> [!CAUTION]
> **File Permissions**: The agent will only have access to `data/notes/`. Access to the rest of the project is restricted for safety.

> [!NOTE]
> **Reminder Persistence**: APScheduler currently uses an in-memory job store. If the bot restarts, pending reminders will be lost unless we switch to a persistent job store (SQLite). For now, we'll stick to in-memory for simplicity.

## Acceptance Criteria
- [ ] Agent can set a reminder for 1 minute and the user receives a message.
- [ ] Agent can save a note "Project Plan" and read it back.
