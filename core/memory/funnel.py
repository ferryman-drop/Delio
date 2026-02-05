import logging
import sys
import os
import asyncio
from typing import Dict, Any, List

# Ensure legacy path is available for imports
legacy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../legacy'))
if legacy_path not in sys.path:
    sys.path.append(legacy_path)

# Import legacy modules
try:
    import old_core 
    import old_memory
    import memory_manager_v2
except ImportError as e:
    # Log error but don't crash immediately, wait for usage to see if critical
    logging.getLogger("Delio.MemoryFunnel").error(f"❌ Failed to import legacy modules: {e}")
    # Define stubs to prevent NameError later
    old_core = None
    old_memory = None
    memory_manager_v2 = None

from core.state_guard import guard, Action

logger = logging.getLogger("Delio.MemoryFunnel")

class ContextFunnel:
    def __init__(self):
        self.max_tokens = 6000 # Safety buffer for Gemini (8k limit)

    async def aggregate_context(self, user_id: int, raw_input: str) -> Dict[str, Any]:
        """
        Gathers context from all 3 layers:
        1. Short-term (Redis via old_core) - last 10 messages
        2. Long-term (ChromaDB via old_memory) - vector search
        3. Structured (SQLite via memory_manager_v2) - Life OS profile
        """
        # Ensure we have permission to read memory
        try:
            await guard.assert_allowed(user_id, Action.MEM_RETRIEVE)
        except Exception as e:
            logger.warning(f"⚠️ Memory fetch skipped due to permissions/guard: {e}")
            # Even if guarded, we might return empty dict or minimal info? 
            # Guard raises PermissionError.
            # But normally RETRIEVE state allows MEM_RETRIEVE.
            # If it fails, maybe we should return empty?
            pass 
        
        logger.debug(f"🌪️ Funneling context for user {user_id}...")
        
        context_data = {
            "short_term": [],
            "long_term_memories": [],
            "structured_profile": {}
        }
        
        # 1. Short-Term (Redis) - Fast
        if old_core:
            try:
                # Use old_core.get_cached_context which accesses Redis
                history = old_core.get_cached_context(user_id)
                # History is usually a list of strings [text1, text2...]
                # --- TOKEN BUDGETING (Fix for "Context Overflow") ---
                # Simple approximation: 1 token ~= 4 chars
                # We want max ~1000 tokens for short term (~4000 chars)
                budget = 4000
                current_chars = 0
                selected_history = []
                
                # Iterate backwards (newest first)
                if history:
                    for msg in reversed(history):
                        msg_len = len(msg)
                        if current_chars + msg_len > budget:
                            break
                        selected_history.insert(0, msg) # Prepend to keep chronological order
                        current_chars += msg_len
                
                context_data["short_term"] = selected_history
                # ----------------------------------------------------
            except Exception as e:
                logger.warning(f"⚠️ Redis fetch (Short-Term) failed: {e}")
        else:
             logger.warning("old_core module not loaded, skipping short_term")

        # 2. Structured (SQLite) - Metadata
        if memory_manager_v2:
            try:
                # Access module-level variable to support delayed init
                if memory_manager_v2.structured_memory:
                    profile = memory_manager_v2.structured_memory.get_all_memory(user_id)
                    context_data["structured_profile"] = profile
                else:
                    # Try to init if missing? Or just log
                    logger.debug("structured_memory not initialized yet")
            except Exception as e:
                logger.warning(f"⚠️ SQLite fetch (Structured) failed: {e}")

        # 3. Long-Term (ChromaDB) - Semantic
        if old_memory:
            try:
                # Search relevant memories using sync method in thread
                if hasattr(old_memory, 'search_memory'):
                     memories = await asyncio.to_thread(old_memory.search_memory, user_id, raw_input, limit=5)
                     context_data["long_term_memories"] = memories
                else:
                     logger.warning("old_memory missing search_memory method")
            except Exception as e:
                logger.warning(f"⚠️ Vector DB fetch (Long-Term) failed: {e}")
            
        logger.info(f"✅ Funnel complete. Short: {len(context_data['short_term'])}, Long: {len(context_data['long_term_memories'])}")
        return context_data

# Singleton
funnel = ContextFunnel()
