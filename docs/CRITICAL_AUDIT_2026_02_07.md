# CRITICAL AUDIT: Delio (AID) v4.1
**Date:** 2026-02-07
**Auditor:** Claude Opus 4.6 (Chief Systems Architect)
**Scope:** Full codebase review — logic, concurrency, architecture, data flow

---

## LEGEND
- **CRITICAL** — App crashes or silently breaks core functionality
- **HIGH** — Logic errors affecting quality, UX, or data integrity
- **MEDIUM** — Architectural debt that will bite at scale
- **LOW** — Code quality, maintainability

---

## CRITICAL

### BUG-001: `extract_attributes()` does not exist
- **File:** `states/memory_write.py:21`
- **Problem:** Calls `llm.extract_attributes(context.raw_input)` but this function is never defined in `core/llm_service.py`
- **Impact:** Every message with `len(raw_input) > 15` triggers `AttributeError`. Swallowed by try/except. SQLite profile updates via this path **never happen**.
- **Fix:** Implement `extract_attributes()` in `llm_service.py` or remove the call.

### BUG-002: `DEEP_THINK` state is unroutable
- **Files:** `core/state_guard.py`, `core/engine.py`, `states/retrieve.py`
- **Problem:**
  1. `State.DEEP_THINK` exists in `state.py`
  2. `retrieve.py` routes to it when `metadata["mode"] == "deep_think"`
  3. But `state_guard._allowed_transitions` has **no entry** for DEEP_THINK
  4. And `engine.py` **never registers** a handler for it
- **Impact:** `guard.enter(user_id, State.DEEP_THINK)` always throws `RuntimeError("FORBIDDEN TRANSITION")`. Deep Think is dead code.
- **Fix:** Add DEEP_THINK to `_allowed_transitions` (RETRIEVE -> DEEP_THINK, DEEP_THINK -> DECIDE/ERROR). Register `DeepThinkState` handler in `engine.py`.

### BUG-003: `SCHEDULE` and `NOTIFY` states — ghost states
- **File:** `core/state_guard.py`, `core/engine.py`
- **Problem:** Present in `_allowed_transitions` but no handlers registered. If FSM reaches them → "No handler" → ERROR.
- **Fix:** Either register handlers or remove from transitions map.

### BUG-004: Dual lock trees — deadlock risk
- **Files:** `core/fsm.py:31-37`, `core/state_guard.py:54-76`
- **Problem:** FSM has `_session_locks` (per-user). StateGuard has `_user_locks` (per-user). Two independent lock hierarchies on the same user_id. FSM holds its lock for the entire processing cycle (line 66), and inside it StateGuard acquires its own lock on every `enter()`.
- **Impact:** With concurrent access to same user_id, lock ordering may not match → deadlock.
- **Fix:** Consolidate to a single lock hierarchy. Either FSM lock OR StateGuard lock, not both.

### BUG-005: `force_idle()` is not thread-safe
- **File:** `core/state_guard.py:192`
- **Problem:** `force_idle()` is synchronous and mutates `_user_states` dict without acquiring `user_lock`. Called in `fsm.py:68` and `fsm.py:119`. If another coroutine holds the user_lock during `guard.enter()` — data race on dict mutation.
- **Fix:** Make `force_idle()` async and acquire the user lock, or document that it must only be called when the session lock is held.

---

## HIGH

### BUG-006: Router blocks event loop (sync API call)
- **File:** `core/router.py:32`
- **Problem:** `self.client.models.generate_content()` is a **synchronous** HTTP call. Not wrapped in `asyncio.to_thread()`. Blocks the entire event loop for every incoming message.
- **Impact:** With 10+ concurrent users the bot freezes.
- **Fix:** Wrap in `await asyncio.to_thread(...)`.

### BUG-007: `time.sleep()` in async code
- **Files:** `core/llm_service.py:71`, `core/llm_service.py:328`, `core/llm_service.py:421`
- **Problem:** Blocking `time.sleep()` inside async functions (`call_actor`, `transcribe_audio`, `call_deep_think`).
- **Fix:** Replace with `await asyncio.sleep()`.

### BUG-008: Singleton duplication — ContextFunnel vs MemoryWriter
- **Files:** `core/memory/funnel.py`, `core/memory/writer.py`
- **Problem:** Both create independent instances of `StructuredMemory`, `RedisManager`, `ChromaManager`. Result: 2x Redis connections, 2x ChromaDB clients, 2x SQLite connections. No coordination.
- **Fix:** Share backend instances. Inject them from a single init point, or make funnel/writer use the same singletons.

### BUG-009: `engine.py` imports legacy modules with fragile path dependency
- **File:** `core/engine.py:24-26`
- **Problem:** `import memory_manager_v2`, `memory_populator`, `model_control` — these live in `/legacy/` and only get added to `sys.path` if `funnel.py` is imported first.
- **Fix:** Explicit sys.path setup in engine.py, or refactor legacy imports.

### BUG-010: Reflection self-evaluation bias
- **File:** `states/reflect.py`
- **Problem:** Uses Gemini Flash to evaluate responses that Gemini Flash generated. Same model grading itself → inflated scores (always 7-8/10). Critic (DeepSeek) is not used for evaluation.
- **Fix:** Use a different model (DeepSeek or Claude) for `evaluate_performance()`, or remove self-evaluation entirely.

### BUG-011: Obsidian full filesystem walk on every request
- **File:** `core/memory/funnel.py:53`
- **Problem:** `os.walk(config.OBSIDIAN_ROOT)` scans entire directory tree on every message. In threadpool, but still slow with many files.
- **Fix:** Index files on startup, use file watcher for changes, or implement caching.

---

## MEDIUM

### BUG-012: No retry / circuit breaker on LLM calls
- **Files:** `core/llm_service.py` (all call_* functions)
- **Problem:** If Gemini/DeepSeek/Claude returns 429 or 503 — single exception, no retry. User gets error.
- **Fix:** Add retry with exponential backoff (tenacity library or manual).

### BUG-013: `cleanup_user_lock()` deletes potentially held locks
- **File:** `core/state_guard.py:196-206`
- **Problem:** Deletes lock from dict without checking if it's acquired. Comment in code acknowledges this.
- **Fix:** Check `lock.locked()` before deletion, or redesign lifecycle.

### BUG-014: SQLite open-close on every call
- **File:** `core/memory/structured.py`
- **Problem:** Every `get_memory()`, `set_memory()`, `get_all_memory()` opens a new `aiosqlite.connect()`. No connection pooling.
- **Fix:** Use a persistent connection or connection pool.

### BUG-015: Memory Writer bypasses StateGuard for Redis/Chroma
- **File:** `states/memory_write.py`
- **Problem:** Only checks `Action.MEMORY_WRITE` once at top. Individual `writer.append_history()` (Redis) and `writer.save_semantic_memory()` (Chroma) have no guard checks. Direct calls to `writer` outside FSM skip all security.
- **Fix:** Add guard checks inside writer methods, or make writer private to MemoryWriteState.

### BUG-016: Image upload without cleanup
- **File:** `core/llm_service.py:65`
- **Problem:** Files uploaded to Gemini File API are never deleted. Quota exhaustion over time.
- **Fix:** Delete uploaded files after use via `client.files.delete()`.

### BUG-017: Heartbeat SKIP detection is fragile
- **File:** `states/decide.py`
- **Problem:** `resp_clean.startswith("SKIP")` depends on exact LLM output formatting. Leading whitespace or newline breaks it → bot sends "SKIP: No changes" as a real message to user.
- **Fix:** Strip more aggressively, or use regex. Consider structured output (JSON) for heartbeat responses.

---

## LOW

### BUG-018: `datetime` imported after usage in digest.py
- **File:** `core/memory/digest.py:87 vs :100`
- **Problem:** `datetime.now()` used on line 87, but `from datetime import datetime` is on line 100. Will crash on first heartbeat that produces lessons.
- **Fix:** Move import to top of file.

### BUG-019: Hardcoded absolute paths
- **Files:** `core/engine.py:84` (`/root/ai_assistant/data/bot_data.db`), `config.py:110` (`/data/obsidian`)
- **Fix:** Use config-driven relative paths.

### BUG-020: Silent exception swallowing everywhere
- **Pattern across:** `states/memory_write.py`, `core/memory/writer.py`, `core/memory/funnel.py`, etc.
- **Problem:** `except Exception as e: logger.error(...)` → continues silently. Makes debugging nearly impossible.
- **Fix:** At minimum, add error counters/metrics. Consider failing loudly for critical paths.

### BUG-021: `genai` import with silent pass
- **File:** `core/llm_service.py:10-16`
- **Problem:** If `google.genai` is not installed, import silently passes. Then `call_actor()` crashes with `NameError: name 'genai' is not defined`.
- **Fix:** Fail fast at import time or check before first use.

---

## SUMMARY

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 5 | Must fix before any testing |
| HIGH | 6 | Must fix before multi-user |
| MEDIUM | 6 | Fix before B2B launch |
| LOW | 4 | Tech debt |

**Working:** Basic single-user text flow (OBSERVE → PLAN → DECIDE → RESPOND → REFLECT → MEMORY_WRITE → IDLE). Actor-Critic synergy. Redis history. Chroma vector search.

**Broken:** Deep Think, extract_attributes, concurrent users, image cleanup, digest lessons, router blocking.
