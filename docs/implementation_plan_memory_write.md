# Memory V2 Writing Integration Plan

**Goal**: Enable Delio to *write* to its new memory system (`Redis`, `SQLite`, `Chroma`) during interaction cycles.

## 1. Components to Create

### `core/memory/writer.py`
A facade class `MemoryWriter` (similar to `ContextFunnel` but for writing) to handle async storage operations without blocking the main FSM loop.
- **Methods**:
    - `append_history(user_id, role, content, model)` -> Redis.
    - `save_semantic_memory(user_id, user_input, bot_response)` -> ChromaDB.
    - `save_lesson(user_id, trigger, observation, correction)` -> SQLite (`lessons_learned`).
    - `update_profile(user_id, key, value, confidence)` -> SQLite (`user_attributes`).

## 2. Components to Modify

### `core/llm_service.py`
- Add `extract_user_attributes(text: str) -> dict`.
    - Uses a small/fast model (Gemini Flash) to extract facts from user input (e.g., "I live in Kyiv" -> `{"location": "Kyiv"}`).
    - Returns structured JSON.

### `core/fsm.py`
- **State: `ACT` / `RESPOND`**
    - Call `memory_writer.append_history` for User input and Bot response.
    - Call `memory_writer.save_semantic_memory` (background task) for the interaction.
    - If `extract_user_attributes` finds data, call `memory_writer.update_profile`.
- **State: `REFLECT`**
    - If `evaluate_performance` returns a lesson, call `memory_writer.save_lesson`.

## 3. Execution Steps
1.  Create `core/memory/writer.py`.
2.  Update `core/llm_service.py` with extraction logic.
3.  Integration into `core/fsm.py`.
4.  Verify with `tests/test_memory_write_flow.py`.
