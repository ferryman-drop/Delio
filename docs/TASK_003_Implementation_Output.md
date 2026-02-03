# TASK-003: Legacy Decoupling — Implementation Output (RESUBMIT)

**Status**: ✅ COMPLETED  
**Implementer**: Implementation Engineer  
**Date**: 2026-02-03  
**Review Feedback**: [TASK_002_003_REVIEW.md](./TASK_002_003_REVIEW.md)

---

## 🔧 Fixes from Review-003

### 1. 🧹 Code Cleanliness
- ✅ Removed internal monologue comments in `core/llm_service.py` (Lines 97-108). Code is now clean and production-ready.

### 2. 🛡️ Import Safety
- ✅ Wrapped `from openai import OpenAI` in `try-except ImportError`.
- Added fallback logging (`Optional dependency 'openai' not found. Skipping Critic phase.`) and graceful degradation (returns Actor response only).

---

## 📦 Changes Summary

### New Files: 2
- `core/llm_service.py`: LLM Adapter Service
- `tests/test_task_003_decoupling.py`: Verification tests

### Files Modified: 1
- `states/plan.py`: Refactored to use `core.llm_service`

---

## 🔧 Implementation Details (Final)

### 1. `core/llm_service.py`
- Implemented `call_actor` (wraps `legacy_core`).
- Implemented `call_critic` (Actor-Critic Synergy).
- **Safety**: Robust imports for `openai` and `legacy_core`.
- **Cleanliness**: No debug comments.

### 2. `states/plan.py`
- Fully decoupled from legacy imports.
- Uses `core.llm_service`.

---

## 🧪 Testing

### Test Suite: `tests/test_task_003_decoupling.py`

| Test Case | Description | Status |
|-----------|-------------|--------|
| `test_plan_state_uses_llm_service` | Verifies `PlanState.execute` calls mock `llm_service` actor/critic instead of legacy. | ✅ PASS |
| `test_module_imports_clean` | Verifies `states/plan.py` imports cleanly. | ✅ PASS |

**Execution**:
```bash
./venv/bin/python3 -m pytest tests/test_task_003_decoupling.py -v
# Result: 2 passed in 8.95s
```

---

## ✅ Acceptance Criteria Verification

- [x] `llm_service.py` clean of comments.
- [x] `openai` import is safe.
- [x] All decoupling logic preserved.

---

## ✍️ Sign-Off
**Ready for Final Merge**: ✅ YES
