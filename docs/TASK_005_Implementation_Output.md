# TASK-005: Conditional Routing — Implementation Output (RESUBMIT)

**Status**: ✅ COMPLETED  
**Implementer**: Implementation Engineer  
**Date**: 2026-02-03  
**Review Feedback**: [TASK_004_005_REVIEW.md](./TASK_004_005_REVIEW.md)

---

## 🔧 Fixes from Review-004-005

### 🐞 Bug in `states/error.py`
- ✅ Fixed detection logic for "Critic rejected".
- Was: `if "Critic rejected" in context.errors` (Exact match).
- Now: `any("Critic rejected" in str(e) for e in context.errors)` (Partial match check).

---

## 📦 Changes Summary

### Files Modified: 2
- `states/plan.py`: Implemented routing logic (Completed previously).
- `states/error.py`: Fixed error message routing logic.

### New Files: 3
- `states/error.py`: Implemented generic Error Handler (missing dependency found).
- `tests/test_task_005_routing.py`: Verification tests for routing.
- `tests/test_task_005_error_state.py`: Verification tests for error messages.

---

## 🔧 Implementation Details

### 1. `states/plan.py`
- Added conditional check at the end of `execute()`:
  - **Critic Rejection**: Checks if `synergy_label` contains "⚠️". Logs warning, adds context error, returns `State.ERROR`.
  - **Empty Response**: Checks if response is None or len < 5. Logs warning, adds context error, returns `State.ERROR`.
  - **Success**: Returns `State.DECIDE`.

### 2. `states/error.py`
- Implemented `ErrorState`.
- **Smart Messaging**: Sends specific "Critic blocked this" message if `Critic rejected` is found in errors (partial match verified).
- Generic apology for other errors.
- Returns `State.IDLE`.

---

## 🧪 Testing

### Test Suite: `tests/test_task_005_routing.py` (Routing Logic)

| Test Case | Description | Status |
|-----------|-------------|--------|
| `test_plan_routing_critic_rejection` | Mocks Critic returning "⚠️", verifies transition to `State.ERROR`. | ✅ PASS |
| `test_plan_routing_empty_response` | Mocks empty actor response, verifies transition to `State.ERROR`. | ✅ PASS |
| `test_plan_routing_success` | Mocks valid response, verifies transition to `State.DECIDE`. | ✅ PASS |

### Test Suite: `tests/test_task_005_error_state.py` (Message Logic)

| Test Case | Description | Status |
|-----------|-------------|--------|
| `test_error_state_critic_message` | Verifies specific Critic error message is sent. | ✅ PASS |
| `test_error_state_generic_message` | Verifies generic error message for other errors. | ✅ PASS |

**Execution**:
```bash
./venv/bin/python3 -m pytest tests/test_task_005_routing.py tests/test_task_005_error_state.py -v
# Result: 5 passed in total
```

---

## ✅ Acceptance Criteria Verification

- [x] Якщо `context.response` порожній -> йдемо в `ERROR`. (Verified)
- [x] Якщо Critic повернув статус помилки -> йдемо в `ERROR`. (Verified)
- [x] Успішна відповідь -> йдемо в `DECIDE`. (Verified)
- [x] `ErrorState` corectly identifies Critic errors and sends improved message. (Verified by new test)

---

## ✍️ Sign-Off
**Ready for Final Merge**: ✅ YES
