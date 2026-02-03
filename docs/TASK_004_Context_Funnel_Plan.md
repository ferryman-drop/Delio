# TASK-004: Implement Context Funnel (Implementation Plan)

## 🚨 Проблема
Стан `RETRIEVE` не виконує свою функцію. Документація (`MEMORY_FUNNEL.md`) описує складну систему збору контексту (short-term, long-term, structured), але файл `core/memory/funnel.py` фізично відсутній. Бот працює "всліпу" або покладається на хаотичні шматки старого коду.

## 🛠️ Запропоновані Зміни

### 1. [CREATE] `core/memory/funnel.py`
Створити клас `ContextFunnel`, який буде єдиною точкою входу для отримання пам'яті.

```python
import logging
from typing import Dict, Any, List
# Import legacy modules (temporary until full migration)
import old_memory as vector_db
import memory_manager as redis_db
from memory_manager_v2 import structured_memory

logger = logging.getLogger("Delio.MemoryFunnel")

class ContextFunnel:
    def __init__(self):
        self.max_tokens = 6000 # Safety buffer for Gemini (8k limit)

    async def aggregate_context(self, user_id: int, raw_input: str) -> Dict[str, Any]:
        """
        Gathers context from all 3 layers:
        1. Short-term (Redis) - last 10 messages
        2. Long-term (ChromaDB) - vector search
        3. Structured (SQLite) - Life OS profile
        """
        logger.debug(f"🌪️ Funneling context for user {user_id}...")
        
        context_data = {
            "short_term": [],
            "long_term_memories": [],
            "structured_profile": {}
        }
        
        # 1. Short-Term (Redis) - Fast
        try:
            # Use existing legacy function, distinct per user
            history = redis_db.get_history(user_id) 
            context_data["short_term"] = history[-10:] # Last 10
        except Exception as e:
            logger.warning(f"⚠️ Redis fetch failed: {e}")

        # 2. Structured (SQLite) - Metadata
        try:
            if structured_memory:
                profile = structured_memory.get_all_memory(user_id)
                context_data["structured_profile"] = profile
        except Exception as e:
            logger.warning(f"⚠️ SQLite fetch failed: {e}")

        # 3. Long-Term (ChromaDB) - Semantic
        try:
            # Search relevant memories
            memories = await vector_db.search_memories(user_id, raw_input, limit=5)
            context_data["long_term_memories"] = memories
        except Exception as e:
            logger.warning(f"⚠️ Vector DB fetch failed: {e}")
            
        logger.info(f"✅ Funnel complete. Memories: {len(context_data['long_term_memories'])}")
        return context_data

# Singleton
funnel = ContextFunnel()
```

### 2. [MODIFY] `states/retrieve.py`
Підключити Funnel до стану.

```python
from core.memory.funnel import funnel # Import new module

class RetrieveState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # ...
        try:
            # OLD: Empty or stub
            # NEW:
            memory_snapshot = await funnel.aggregate_context(
                user_id=context.user_id,
                raw_input=context.raw_input
            )
            
            # Save into Context
            context.memory_context = memory_snapshot
            
            return State.PLAN
        except Exception as e:
             # ...
```

## 🧪 Verification Plan

### Manual Verification
1. Надіслати повідомлення: "Мене звати Олексій".
2. Зробити `/snapshot` (зберегти в SQLite).
3. Перезавантажити бота (очистити RAM).
4. Надіслати: "Як мене звати?".
5. **Очікувана поведінка**:
   - Лог показує `✅ Funnel complete`.
   - `context.memory_context` містить дані з SQLite/Vector.
   - Бот відповідає: "Вас звати Олексій".

## ✅ Acceptance Criteria
- [ ] Створено файл `core/memory/funnel.py`.
- [ ] Стан `RETRIEVE` викликає `funnel.aggregate_context`.
- [ ] Повертається словник з ключами `short_term`, `long_term_memories`, `structured_profile`.
- [ ] Збої однієї з баз даних (напр. Redis) не крашать весь бот (graceful degradation).
