
import logging
import redis
import os

logger = logging.getLogger(__name__)

# Initialize Redis
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("✅ Prefs: Redis connected")
except Exception as e:
    logger.warning(f"⚠️ Prefs: Redis connection failed: {e}. Using in-memory fallback.")
    redis_client = None

# In-memory fallback
_user_prefs = {}

def get_user_pref(user_id: int) -> str | None:
    """Отримати користувацькі налаштування моделі (pref)"""
    try:
        if redis_client:
            v = redis_client.get(f"preferred_model:{user_id}")
            return v
    except Exception as e:
        logger.error(f"Prefs error: {e}")
    return _user_prefs.get(user_id)

def set_user_pref(user_id: int, model_name: str):
    """Встановити перевагу моделі для користувача"""
    try:
        if redis_client:
            if model_name:
                redis_client.setex(f"preferred_model:{user_id}", 86400 * 30, model_name)
            else:
                redis_client.delete(f"preferred_model:{user_id}")
    except Exception as e:
        logger.error(f"Prefs error: {e}")
    
    if model_name:
        _user_prefs[user_id] = model_name
    else:
        _user_prefs.pop(user_id, None)
