import redis.asyncio as redis
import logging
import json
from typing import List, Dict, Optional
import os

logger = logging.getLogger("Delio.Memory.Redis")

class RedisManager:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_url = f"redis://{host}:{port}/{db}"
        self.client: Optional[redis.Redis] = None
        
    async def connect(self):
        """Initialize Redis connection pool"""
        if not self.client:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            try:
                await self.client.ping()
                logger.info(f"✅ Redis connected at {self.redis_url}")
            except Exception as e:
                logger.error(f"❌ Redis connection failed: {e}")
                self.client = None

    async def close(self):
        if self.client:
            await self.client.close()

    async def append_history(self, user_id: int, role: str, content: str, model: str = None):
        """Append a message to the user's short-term history list"""
        if not self.client:
            logger.warning(f"⚠️ Redis unavailable — short-term memory disabled for user {user_id}")
            return
        
        key = f"history:{user_id}"
        message = {
            "role": role,
            "content": content,
            "model": model  # Optional metadata
        }
        
        try:
            # Push to right (end)
            await self.client.rpush(key, json.dumps(message))
            # Trim to max 20 items to keep it lightweight (Process logic handles loading specific amount)
            await self.client.ltrim(key, -20, -1)
            # Set TTL (e.g., 24 hours)
            await self.client.expire(key, 86400)
        except Exception as e:
            logger.error(f"Redis append error: {e}")

    async def get_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        if not self.client:
            logger.warning(f"⚠️ Redis unavailable — returning empty history for user {user_id}")
            return []
        
        key = f"history:{user_id}"
        try:
            # Get last N items
            items = await self.client.lrange(key, -limit, -1)
            return [json.loads(i) for i in items]
        except Exception as e:
            logger.error(f"Redis fetch error: {e}")
            return []

    async def clear_history(self, user_id: int):
        if not self.client: return
        await self.client.delete(f"history:{user_id}")
