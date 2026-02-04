# ✅ CODER TASK: FSM Hardening & Vision Stability (Completed)

## 🎯 Objective
Resolve the issues causing Vision analysis to timeout and the FSM to crash during tool-use reflection.

## 🧱 Work Zones

### 1. Critic Timeout (`core/llm_service.py`)
- **Problem**: DeepSeek API sometimes hangs, causing the whole FSM to timeout (30s) and deliver nothing to the user.
- **Action**: Wrap the `call_critic` logic in `asyncio.wait_for`.
- **Logic**: 
  - Set timeout to **15 seconds**.
  - If it times out, `except asyncio.TimeoutError`:
    - Log a warning: `⚠️ Critic timeout. Falling back to Actor response.`
    - Return `(actor_response, "♊⚠️ (Timeout)")`.

### 2. Forbidden Transition (`core/state_guard.py`)
- **Problem**: When a tool returns output, the system tries to go from `REFLECT` back to `PLAN` to integrate data, but `StateGuard` blocks it (`REFLECT -> PLAN` is not allowed).
- **Action**: Add `State.PLAN` to the allowed transitions for `State.REFLECT`.
- **Location**: `self._allowed_transitions[State.REFLECT] = [State.MEMORY_WRITE, State.PLAN, State.ERROR]`.

### 3. Cleanup & Restart
- **Action**: Ensure only ONE bot process is running.
- **Command**: `pkill -f python3` then `python3 main.py`.

## 📜 Acceptance Criteria
1.  Photo upload should never result in a "30s Timeout". If Critic is slow, the Gemini response (which takes ~5s) should be delivered.
2.  Log should show successful `ACT -> REFLECT -> PLAN` transitions for tool calls.
3.  User receives the "Polopiryna" description.

---
**Status**: ✅ **COMPLETED** (2026-02-04)
- Critic timeout implemented (15s).
- REFLECT -> PLAN transition allowed in StateGuard.
- Bot restarted and verified.
