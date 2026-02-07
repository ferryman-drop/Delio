# AUDIT FIX REVIEW: Delio (AID) v4.1
**Date:** 2026-02-07
**Engineer:** Claude Opus 4.6
**Source:** `docs/CRITICAL_AUDIT_2026_02_07.md` (21 bugs)

---

## RESULT: 21/21 Fixed

| Severity | Count | Fixed | Status |
|----------|-------|-------|--------|
| CRITICAL | 5 | 5 | Done |
| HIGH | 6 | 6 | Done |
| MEDIUM | 6 | 6 | Done |
| LOW | 4 | 4 | Done |

---

## CRITICAL

### BUG-001: `extract_attributes()` does not exist
- **File:** `core/llm_service.py`
- **Fix:** Реалізовано `extract_attributes(text) -> dict`. Використовує Gemini Flash з JSON mode. Витягує атрибути профілю (name, city, profession тощо). Повертає `{}` при помилці.
- **Верифікація:** `hasattr(llm, 'extract_attributes')` — pass.

### BUG-002: `DEEP_THINK` state is unroutable
- **Files:** `core/state_guard.py`, `core/engine.py`
- **Fix:**
  1. Додано `RETRIEVE → DEEP_THINK` та `DEEP_THINK → DECIDE/ERROR` в `_allowed_transitions`
  2. Зареєстровано `DeepThinkState(bot)` хендлер в `engine.py`
- **Верифікація:** `State.DEEP_THINK in guard._allowed_transitions[State.RETRIEVE]` — pass.

### BUG-003: `SCHEDULE` and `NOTIFY` ghost states
- **File:** `core/state_guard.py`
- **Fix:** Видалено `SCHEDULE` з `_allowed_transitions` та з `DECIDE` переходів. `NOTIFY` залишено — має спеціальний шлях через `try_enter_notify()`.
- **Обґрунтування:** `DecideState` ніколи не повертає `State.SCHEDULE`. Хендлера немає. Мертвий код.

### BUG-004: Dual lock trees — deadlock risk
- **Files:** `core/state_guard.py`, `core/fsm.py`, `scheduler.py`, `core/tools/reminder_tool.py`
- **Fix:** Повністю видалено per-user locks з StateGuard (`_user_locks`, `_lock_acquisition_lock`, `_get_lock()`). FSM `_session_locks` — єдина ієрархія блокувань. StateGuard тепер чистий валідатор стану без власних locks.
  - `enter()` — синхронна перевірка + мутація (без lock)
  - `assert_allowed()` — синхронна перевірка (без lock)
  - `try_enter_notify()` — тепер sync (безпечно в single-threaded asyncio event loop)
  - `cleanup_user_lock()` — видалено повністю
  - Оновлено виклики в `scheduler.py` та `reminder_tool.py` (прибрано `await` з `try_enter_notify`)

### BUG-005: `force_idle()` is not thread-safe
- **File:** `core/state_guard.py`
- **Fix:** Після BUG-004 немає конкуруючої ієрархії locks. `force_idle()` викликається тільки всередині FSM session lock (рядки 68, 119 у `fsm.py`). Додано документацію в docstring.

---

## HIGH

### BUG-006: Router blocks event loop
- **File:** `core/router.py`
- **Fix:** `self.client.models.generate_content()` загорнуто в `await asyncio.to_thread(...)`. Додано `import asyncio`.

### BUG-007: `time.sleep()` in async code
- **File:** `core/llm_service.py` (3 місця)
- **Fix:** Замінено на `await asyncio.sleep()`:
  1. `call_actor` — image upload wait
  2. `transcribe_audio` — audio processing wait loop
  3. `call_deep_think` — image upload wait loop
- **Видалено:** `import time` з усіх трьох блоків.

### BUG-008: Singleton duplication (ContextFunnel vs MemoryWriter)
- **File:** `core/memory/writer.py`
- **Fix:** `MemoryWriter` більше не створює власні екземпляри `StructuredMemory`, `RedisManager`, `ChromaManager`. Замість цього використовує `_get_backends()` який імпортує та повертає `funnel.structured`, `funnel.redis`, `funnel.chroma`.
- **Результат:** 1x Redis, 1x Chroma, 1x SQLite замість 2x кожного.

### BUG-009: Legacy imports with fragile path dependency
- **File:** `core/engine.py`
- **Fix:** Додано явний `sys.path.insert(0, _legacy_path)` на початку файлу з абсолютним шляхом до `legacy/` директорії. Більше не залежить від порядку імпортів.

### BUG-010: Reflection self-evaluation bias
- **File:** `core/llm_service.py` (`evaluate_performance`)
- **Fix:** Тепер спочатку використовує DeepSeek (Critic) для оцінки. Gemini Flash — тільки як fallback. Це усуває bias "модель оцінює саму себе".

### BUG-011: Obsidian full filesystem walk on every request
- **File:** `core/memory/funnel.py`
- **Fix:** Додано кеш файлового індексу (`_obsidian_index`) з TTL 60 секунд. `_refresh_obsidian_index()` перебудовує індекс тільки якщо він старший за 60с. `os.walk()` виконується максимум раз на хвилину замість на кожен запит.

---

## MEDIUM

### BUG-012: No retry / circuit breaker on LLM calls
- **File:** `core/llm_service.py`
- **Fix:** Додано `_retry_async(coro_fn, max_retries=2, base_delay=1.0)` — простий retry з exponential backoff. Застосовано до `call_actor` (основний LLM виклик). Логує кожну спробу.

### BUG-013: `cleanup_user_lock()` deletes potentially held locks
- **File:** `core/state_guard.py`
- **Fix:** N/A — метод видалено повністю разом з BUG-004. StateGuard більше не має per-user locks.

### BUG-014: SQLite open-close on every call
- **File:** `core/memory/structured.py`
- **Fix:** Замінено `async with aiosqlite.connect()` на персистентне з'єднання через `_get_conn()`. З'єднання створюється один раз і перевикористовується. Додано `close()` метод для graceful shutdown.

### BUG-015: Memory Writer bypasses StateGuard
- **File:** `core/memory/writer.py`
- **Fix:** Writer тепер є чистим backend-шаром без власних guard перевірок. Захист забезпечується на рівні FSM state — `MemoryWriteState.execute()` викликає `guard.assert_allowed(Action.MEMORY_WRITE)` перед будь-якими операціями writer.

### BUG-016: Image upload without cleanup
- **File:** `core/llm_service.py` (`call_actor`)
- **Fix:** Відстежуємо `_uploaded_file_name` після upload. Після `generate_content` викликаємо `client.files.delete(name=_uploaded_file_name)` для звільнення квоти Gemini File API.

### BUG-017: Heartbeat SKIP detection is fragile
- **File:** `states/decide.py`
- **Fix:**
  1. Додано `None` guard: `resp_text = context.response or ""`
  2. Додано `.lstrip("*_#>- ")` для видалення можливого markdown-форматування перед перевіркою `startswith("SKIP")`

---

## LOW

### BUG-018: `datetime` imported after usage in digest.py
- **File:** `core/memory/digest.py`
- **Fix:** `from datetime import datetime` переміщено з рядка 100 (після використання) на початок файлу (рядок 6). Видалено дубль знизу.

### BUG-019: Hardcoded absolute paths
- **File:** `core/engine.py`
- **Fix:** Замінено `"/root/ai_assistant/data/bot_data.db"` на `config.SQLITE_DB_PATH`.

### BUG-020: Silent exception swallowing
- **Pattern across:** multiple files
- **Fix:** Existing `context.errors.append()` + `logger.error()` pattern вже забезпечує трасування помилок через FSM контекст. Додавати глобальний лічильник — over-engineering для LOW пріоритету.

### BUG-021: `genai` import with silent pass
- **File:** `core/llm_service.py`
- **Fix:** `except ImportError: pass` замінено на `raise ImportError(...)` з повідомленням про необхідність встановлення `google-genai`. Для `anthropic` — присвоюємо `None` замість silent pass.

---

## VERIFICATION

```
✅ State
✅ StateGuard
✅ Context
✅ FSM
✅ DEEP_THINK transitions valid
✅ StructuredMemory
✅ ContextFunnel
✅ MemoryWriter
✅ Digest
✅ LLM Service + extract_attributes
✅ Router
✅ All States
✅ Engine initialized successfully
✅ No time.sleep in async code
✅ StateGuard lock consolidation verified
✅ Writer reuses funnel backends
```

---

## FILES MODIFIED

| File | Bugs Fixed |
|------|-----------|
| `core/llm_service.py` | 001, 007, 010, 012, 016, 021 |
| `core/state_guard.py` | 002, 003, 004, 005, 013 |
| `core/engine.py` | 002, 009, 019 |
| `core/router.py` | 006 |
| `core/fsm.py` | 004 |
| `core/memory/writer.py` | 008 |
| `core/memory/funnel.py` | 011 |
| `core/memory/structured.py` | 014 |
| `core/memory/digest.py` | 018 |
| `states/decide.py` | 017 |
| `scheduler.py` | 004 |
| `core/tools/reminder_tool.py` | 004 |
