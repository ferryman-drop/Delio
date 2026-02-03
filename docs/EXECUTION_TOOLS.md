# 🛠️ Module: Execution & Tools

This is the system's interface with the real world (Filesystem, Web, Docker).

## 📁 Key Files
- `tools.py`: The library of available functions.
- `states/act.py`: The handler that interprets and runs tool calls.

## 🧰 Available Tools
- **Web Search**: DuckDuckGo integration for real-time info.
- **Python Execution**: Isolated code execution.
- **Project Control**: `read_project_file`, `edit_project_file` (for self-improvement).
- **Communication**: `switch_model`, `save_user_note`.

## 🛡️ Clarification: Tool Guard Assertions
Every function in `tools.py` is protected by a Guard assertion:
```python
def search_web(query: str):
    guard.assert_allowed(Action.NETWORK)
    # ... logic ...
```
Even if the AI "hallucinates" a tool call in the `PLAN` state, the `StateGuard` will raise a `PermissionError` because `Action.NETWORK` is only permitted in the `ACT` state.

## 🏗️ Sandbox (The Next Step)
Currently, tools run in the local environment (protected by `StateGuard`). The roadmap includes migrating all `ACT` operations into a isolated Docker sandbox for true autonomy without risk to the host system.
