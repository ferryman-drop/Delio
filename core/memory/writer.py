import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import config

logger = logging.getLogger("Delio.MemoryWriter")

class MemoryWriter:
    def __init__(self):
        self._init_done = False

    def _get_backends(self):
        """Reuse singleton backends from ContextFunnel to avoid duplication."""
        from core.memory.funnel import funnel
        return funnel.structured, funnel.redis, funnel.chroma

    async def initialize(self):
        """Lazy init via funnel"""
        if self._init_done: return
        from core.memory.funnel import funnel
        await funnel.initialize()
        self._init_done = True

    async def append_history(self, user_id: int, role: str, content: str, model: str = None):
        """Write to short-term memory (Redis)"""
        if not self._init_done: await self.initialize()
        try:
            _, redis, _ = self._get_backends()
            await redis.append_history(user_id, role, content, model)
        except Exception as e:
            logger.error(f"Redis write failed: {e}")

    async def save_semantic_memory(self, user_id: int, user_input: str, bot_response: str, metadata: dict = None):
        """Write to vector memory (Chroma)"""
        if not self._init_done: await self.initialize()
        try:
            _, _, chroma = self._get_backends()

            # 1. User Input
            meta_user = metadata.copy() if metadata else {}
            meta_user.update({"role": "user", "type": "interaction"})
            await chroma.store_memory(user_id, user_input, meta_user)

            # 2. Bot Response
            meta_bot = metadata.copy() if metadata else {}
            meta_bot.update({"role": "assistant", "type": "interaction"})
            await chroma.store_memory(user_id, bot_response, meta_bot)

        except Exception as e:
            logger.error(f"Chroma write failed: {e}")

    async def save_lesson(self, user_id: int, trigger: str, observation: str, correction: str):
        """
        Write reflection lesson (Structured Memory -> feedback_signals)
        Mapping 'lessons' to 'feedback_signals' section.
        """
        if not self._init_done: await self.initialize()
        try:
            structured, _, _ = self._get_backends()
            lesson_data = {
                "trigger": trigger,
                "observation": observation,
                "correction": correction,
                "timestamp": datetime.now().isoformat()
            }
            key = f"lesson_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            await structured.set_memory(
                user_id,
                section="feedback_signals",
                key=key,
                value=lesson_data,
                confidence=0.8
            )
            logger.info(f"💾 Lesson saved for user {user_id}")
        except Exception as e:
            logger.error(f"Structured lesson write failed: {e}")

    async def update_attribute(self, user_id: int, key: str, value: str, confidence: float = 0.8):
        """
        Update user profile attribute (Structured Memory -> core_identity or misc)
        """
        if not self._init_done: await self.initialize()
        try:
            structured, _, _ = self._get_backends()
            section = "core_identity"

            await structured.set_memory(
                user_id,
                section=section,
                key=key,
                value=value,
                confidence=confidence
            )
            logger.info(f"💾 Attribute '{key}' updated for user {user_id}")
        except Exception as e:
            logger.error(f"Structured attribute write failed: {e}")

    async def close(self):
        pass  # Lifecycle owned by funnel

# Singleton
writer = MemoryWriter()
