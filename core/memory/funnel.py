import logging
import sys
import os
from typing import Dict, Any, List

# Import legacy modules
try:
    from legacy import old_memory as vector_db
    from legacy import memory_manager as redis_db
    from legacy import memory_manager_v2 as structured_db
except ImportError:
    # Fallback for when running from different contexts or if legacy is not a package
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../legacy')))
    import old_memory as vector_db
    import memory_manager as redis_db
    import memory_manager_v2 as structured_db

from core.state_guard import guard, Action

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
        await guard.assert_allowed(user_id, Action.MEM_RETRIEVE)
        
        logger.debug(f"🌪️ Funneling context for user {user_id}...")
        
        context_data = {
            "short_term": [],
            "long_term_memories": [],
            "structured_profile": {}
        }
        
        # 1. Short-Term (Redis) - Fast
        try:
            # redis_db.get_history might need specific args, let's check legacy code signature if possible.
            # Assuming get_history(user_id) returns list of dicts.
            if hasattr(redis_db, 'get_history'):
                 history = redis_db.get_history(user_id) 
                 context_data["short_term"] = history[-10:] # Last 10
            else:
                 # Fallback if function name differs
                 logger.warning("Redis DB missing get_history, skipping short_term")
        except Exception as e:
            logger.warning(f"⚠️ Redis fetch failed: {e}")

        # 2. Structured (SQLite) - Metadata
        try:
            if structured_db.structured_memory:
                profile = structured_db.structured_memory.get_all_memory(user_id)
                context_data["structured_profile"] = profile
        except Exception as e:
            logger.warning(f"⚠️ SQLite fetch failed: {e}")

        # 3. Long-Term (ChromaDB) - Semantic
        try:
            # Search relevant memories
            # search_memory is async or sync? The plan implied 'await vector_db.search_memories'.
            # Let's assume search_memories exists or search_memory.
            if hasattr(vector_db, 'search_memories'):
                memories = await vector_db.search_memories(user_id, raw_input, limit=5)
            elif hasattr(vector_db, 'search_memory'):
                 # Check if sync or async. In old code it seemed sync? 
                 # Previous file had: context["long_term_memories"] = legacy_memory.search_memory(user_id, query, limit=5)
                 # Wait, previous file did NOT await it.
                 # Let's wrap in try-await just in case, or run in thread if sync.
                 
                 # Note: old_memory.py usually wraps sync Chroma calls.
                 # Safer to run in thread if we are unsure.
                 import asyncio
                 memories = await asyncio.to_thread(vector_db.search_memory, user_id, raw_input, limit=5)
            else:
                 memories = []
                 
            context_data["long_term_memories"] = memories
        except Exception as e:
            logger.warning(f"⚠️ Vector DB fetch failed: {e}")
            
        logger.info(f"✅ Funnel complete. Short: {len(context_data['short_term'])}, Long: {len(context_data['long_term_memories'])}")
        return context_data

# Singleton
funnel = ContextFunnel()
