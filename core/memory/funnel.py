import logging
import asyncio
import sys
import os
import time as _time
from typing import Dict, Any, List
import config

# Ensure legacy path is available for imports
legacy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../legacy'))
if legacy_path not in sys.path:
    sys.path.append(legacy_path)

from core.state_guard import guard, Action
from core.memory.structured import StructuredMemory
from core.memory.redis_storage import RedisManager
from core.memory.chroma_storage import ChromaManager

logger = logging.getLogger("Delio.MemoryFunnel")

class ContextFunnel:
    def __init__(self):
        self.structured = StructuredMemory(config.SQLITE_DB_PATH)
        self.redis = RedisManager(config.REDIS_HOST, config.REDIS_PORT)
        self.chroma = ChromaManager(config.CHROMA_DB_PATH)
        self._init_done = False
        self._obsidian_index = None  # Cached file list: [(path, mtime)]
        self._obsidian_index_time = 0  # Timestamp of last index

    async def initialize(self):
        """Async initialization of all backends"""
        if self._init_done: return
        try:
            await self.structured.init_db()
            await self.redis.connect()
            await self.chroma.init_db()
            self._init_done = True
            logger.info("✅ ContextFunnel backends initialized")
        except Exception as e:
            logger.error(f"❌ ContextFunnel init failed: {e}")

    def _refresh_obsidian_index(self):
        """Rebuild file index if stale (>60s) or missing."""
        now = _time.time()
        if self._obsidian_index is not None and (now - self._obsidian_index_time) < 60:
            return
        index = []
        for root, dirs, files in os.walk(config.OBSIDIAN_ROOT):
            for file in files:
                if file.endswith(".md"):
                    index.append(os.path.join(root, file))
        self._obsidian_index = index
        self._obsidian_index_time = now

    async def _search_obsidian(self, query: str) -> List[str]:
        """Simple keyword search in Obsidian Vault with cached file index"""
        if not os.path.exists(config.OBSIDIAN_ROOT) or len(query) < 3:
            return []

        try:
            def scan():
                self._refresh_obsidian_index()
                found = []
                query_lower = query.lower()
                keywords = [k for k in query_lower.split() if len(k) > 3]
                if not keywords: return []

                for path in self._obsidian_index:
                    try:
                        file = os.path.basename(path)
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                            content_lower = content.lower()

                            score = 0
                            if query_lower in file.lower(): score += 5
                            for k in keywords:
                                if k in content_lower: score += 1

                            if score > 0:
                                snippet = content[:500].replace("\n", " ")
                                found.append(f"🕸️ [Obsidian] [[{file}]]: {snippet}...")
                                if len(found) >= 3: return found
                    except: continue
                return found

            return await asyncio.to_thread(scan)
        except Exception as e:
            logger.warning(f"Obsidian search error: {e}")
            return []

    async def aggregate_context(self, user_id: int, raw_input: str) -> Dict[str, Any]:
        """
        Gathers context from all 3 layers:
        1. Short-term (Redis) - Recent chat history
        2. Long-term (ChromaDB) - Semantic search
        3. Structured (StructuredMemory) - 9-Section profile
        4. Obsidian (File Search) - Keyword match
        """
        if not self._init_done:
            await self.initialize()

        # Ensure we have permission
        try:
            await guard.assert_allowed(user_id, Action.MEM_RETRIEVE)
        except Exception as e:
            logger.warning(f"⚠️ Memory fetch blocked by guard: {e}")
            return {"short_term": [], "long_term_memories": [], "structured_profile": {}}

        logger.debug(f"🌪️ Funneling context for user {user_id}...")
        
        context_data = {
            "short_term": [],
            "long_term_memories": [],
            "structured_profile": {},
            "feedback_signals": [] # lessons
        }

        # Parallel Fetching for Speed
        try:
            results = await asyncio.gather(
                self.redis.get_history(user_id, limit=10),
                self.chroma.search(user_id, raw_input, limit=5),
                self.structured.get_all_memory(user_id, min_confidence=0.4),
                self._search_obsidian(raw_input),
                return_exceptions=True
            )
            
            # Unpack results
            short_term, long_term, full_memory, obsidian_hits = results

            if isinstance(short_term, list):
                context_data["short_term"] = short_term
            else:
                logger.error(f"Redis fetch failed: {short_term}")

            if isinstance(long_term, list):
                context_data["long_term_memories"] = long_term
            else:
                logger.error(f"Chroma fetch failed: {long_term}")

            # Merge Obsidian hits into long_term_memories
            if isinstance(obsidian_hits, list) and obsidian_hits:
                logger.info(f"🕸️ Found {len(obsidian_hits)} Obsidian matches")
                context_data["long_term_memories"].extend(obsidian_hits)

            if isinstance(full_memory, dict):
                # Extract specific sections for context
                context_data["structured_profile"] = full_memory
                
                if "feedback_signals" in full_memory:
                     context_data["feedback_signals"] = full_memory["feedback_signals"]
            else:
                logger.error(f"Structured memory fetch failed: {full_memory}")

        except Exception as e:
            logger.error(f"❌ Critical Funnel Error: {e}")

        logger.info(f"✅ Context Aggregated: {len(context_data['short_term'])} recent, {len(context_data['long_term_memories'])} memories")
        return context_data

    async def close(self):
        await self.redis.close()

# Singleton
funnel = ContextFunnel()
