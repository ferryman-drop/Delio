import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Retrieve")

class RetrieveState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # 1. Short-term memory (Recent messages cache)
        import core as legacy_core
        recent_context = legacy_core.get_cached_context(context.user_id)
        context.memory_context["recent_messages"] = recent_context
        
        # 2. Long-term memory (ChromaDB)
        import memory as legacy_memory
        if legacy_memory.collection:
            memories = legacy_memory.search_memory(context.user_id, context.raw_input)
            context.memory_context["long_term"] = memories
        
        # 3. Structured memory (SQLite)
        import memory_manager_v2 as legacy_mm2
        if legacy_mm2.structured_memory:
            structured = legacy_mm2.structured_memory.get_all_memory(context.user_id)
            context.memory_context["structured"] = structured
            
        logger.debug(f"🧠 Memory retrieved for user {context.user_id}")
        return State.PLAN
