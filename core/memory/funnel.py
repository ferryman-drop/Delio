import logging
import old_core as legacy_core
import old_memory as legacy_memory
import memory_manager_v2 as legacy_mm2
from core.state_guard import guard, Action
from typing import Dict, List, Any, Optional

logger = logging.getLogger("Delio.MemoryFunnel")

class ContextFunnel:
    """
    Consolidates multiple memory sources into a single structured context.
    - Short-term: Redis recent messages
    - Long-term: ChromaDB vector search
    - Structured: SQLite profile & facts (V2)
    """
    
    @staticmethod
    async def get_all_context(user_id: int, query: str) -> Dict[str, Any]:
        """
        Aggregate context from all sources.
        """
        guard.assert_allowed(user_id, Action.MEM_RETRIEVE)
        context = {
            "recent_messages": [],
            "long_term_memories": [],
            "structured_profile": {},
            "raw_query": query
        }

        # 1. Short-term (Recent messages from Redis)
        try:
            context["recent_messages"] = legacy_core.get_cached_context(user_id)
        except Exception as e:
            logger.error(f"Error fetching short-term memory: {e}")

        # 2. Long-term (ChromaDB Vector Search)
        try:
            if legacy_memory.collection:
                context["long_term_memories"] = legacy_memory.search_memory(user_id, query, limit=5)
        except Exception as e:
            logger.error(f"Error fetching long-term memory: {e}")

        # 3. Structured (SQLite Memory V2)
        try:
            if legacy_mm2.structured_memory:
                context["structured_profile"] = legacy_mm2.structured_memory.get_all_memory(user_id, min_confidence=0.3)
        except Exception as e:
            logger.error(f"Error fetching structured memory: {e}")

        return context
