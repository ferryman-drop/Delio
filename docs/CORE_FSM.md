# 🤖 Module: Core FSM & State Guard

The "Brain" of Delio. This module manages the lifecycle of every interaction and enforces the project's safety boundaries.

## 📁 Key Files
- `core/fsm.py`: The `FSMController`. Manages state transitions and event loops.
- `core/state.py`: Definition of all allowed `State` enums.
- `core/state_guard.py`: The `StateGuard` (Hypervisor). Blocks forbidden actions.
- `core/context.py`: The `ExecutionContext`. A "black box" that carries data through the states.

## 🛡️ State Guard: Action Matrix
The Guard ensures that side-effects only happen in specific states:

| Action | Allowed States | Description |
| :--- | :--- | :--- |
| `LLM_CALL` | `PLAN`, `REFLECT` | Prevents infinite AI loops during observation/action. |
| `FS_WRITE` | `ACT` | Blocks AI from changing project files unless explicitly executing a plan. |
| `NETWORK` | `ACT`, `RESPOND` | Limits external access to delivery or tools. |
| `MEM_RETRIEVE`| `RETRIEVE` | Ensures structured context loading. |
| `MEM_WRITE` | `MEMORY_WRITE` | Protects the integrity of long-term memory. |

## 🧩 Clarification: Transition Invariants
You cannot skip steps. For example:
- `IDLE` → `OBSERVE` (✅ Allowed: New message)
- `PLAN` → `ACT` (❌ FORBIDDEN: Must pass through `DECIDE` for validation)
- `ANY` → `ERROR` (✅ Allowed: Emergency shutdown)

## 🛠️ How to Extend
To add a new capability:
1. Define a new `State` in `core/state.py`.
2. Update the `allowed_transitions` map in `core/state_guard.py`.
3. Create a handler in `states/` and register it in `main.py`.
