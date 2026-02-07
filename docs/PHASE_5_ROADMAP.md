# PHASE 5.0: UNIFICATION & SYSTEM 2 EVOLUTION

**Status**: Planning
**Target Version**: 3.0.0
**Context**: We have two potential Memory V2 systems:
1. `core/memory/sqlite_storage.py` (Simple, created in Phase 4)
2. `legacy/memory_manager_v2.py` (Advanced, 9-section, exists but labeled legacy)

**Decision**: **Adopt & Promote `memory_manager_v2.py`**. It is feature-rich (Confidence, TTL, Snapshots).

## 1. 🧬 Unification (The "Great Merge")
*Goal: One Memory System to rule them all.*

- **Action**: Move `legacy/memory_manager_v2.py` -> `core/memory/structured.py`.
- **Action**: Refactor `core/memory/writer.py` to use `StructuredMemory`.
- **Action**: Delete `core/memory/sqlite_storage.py` (Redundant).
- **Migration**: Run `scripts/migrate_to_memory_v2.py` (moved from `legacy/`).

## 2. � The Heartbeat (Optimization)
*Goal: Tune the existing Heartbeat for richer interactions.*

- **Current Status**: Implemented in `scheduler.py` & `force_heartbeat.py`.
- **Upgrade**:
    - Connect Heartbeat to `StructuredMemory` (e.g., "Check `goals` confidence").
    - Enable `digest_daily_logs` (currently commented out).

## 3. 🧠 System 2 Thinking
*Goal: Deep Research capabilities.*

- New State: `DEEP_THINK`.
- Logic: Recursive web search / planning before answering.

## 4. 🎛️ The Dashboard
*Goal: Visualization.*

- Web UI to view the 9 Memory Sections (`core_identity`, `goals`, etc.).

---

## 📅 Execution Plan

### Sprint 5.1: Unification
- [ ] Promote `legacy/memory_manager_v2.py` to Core.
- [ ] Connect `writer.py` to `StructuredMemory`.
- [ ] Run Migration.

### Sprint 5.2: System 2
- [ ] Implement `DEEP_THINK` state.
- [ ] Enable Daily Digest.
