# 📋 REVIEW-003: Safety Guards & Legacy Decoupling

**Date**: 2026-02-03  
**Reviewer**: The Critic (AGI-lite Kernel)  

---

## 🟢 PART 1: Task 002 (Safety Guards)

**Decision**: **[APPROVE]** ✅

### 🔍 Analysis
- **Spec Compliance**: 10/10. All requested features (timeout, loop counter, max transitions) implemented.
- **Safety**: Excellent. Limits are enforced strictly. `finally` block ensures lock cleanup, preserving Task 001 achievements.
- **Testing**: `test_infinite_loop_trap` cleverly mocks the strict guard rules to test the loop counter.

### 📝 Notes
- The use of `asyncio.timeout` wrapping the entire process is a robust solution against zombie tasks.

---

## 🟡 PART 2: Task 003 (Legacy Decoupling)

**Decision**: **[REJECT - MINOR CHANGES REQUESTED]** ❌

### 🔍 Analysis
- **Architecture**: Good. The `PlanState` is now clean of legacy imports. The `LLMService` adapter acts as a proper facade.
- **Functionality**: Logic preserved correctly during migration.

### ⛔ Issues (Must Fix)

#### 1. 🧹 **Code Cleanliness (Comments Junk)**
**File**: `core/llm_service.py`  
**Lines**: 97-108

**Problem**:
There is a block of "inner monologue" comments left in the code:
```python
# Wait, previous logic was:
# if validated: return clean, "♊+🐋"
# else: return (implied None?) No, previous code...
```
This is **unacceptable** for production code. It confuses future maintainers.

**Action**: Delete these lines. Keep the logic, remove the monologue.

#### 2. 🛡️ **Import Safety**
**File**: `core/llm_service.py`  
**Lines**: 56 (inside `call_critic`)

**Problem**:
```python
from openai import OpenAI
```
If `openai` package is not installed (e.g., in a minimal env), this crashes the Critic phase hard.

**Action**: Wrap this import in `try-except ImportError` and log a warning if missing (returning fallback response), just like you did for `legacy_core`.

---

## 🚀 Next Steps

1. **Delete** the internal monologue comments in `core/llm_service.py`.
2. **Add** safety wrapper for `openai` import.
3. **Resubmit** Task 003.

Task 002 is ready to merge. Task 003 needs 5 minutes of cleanup.
