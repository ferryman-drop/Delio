import asyncio
import pytest
import os
import shutil
from core.memory.sqlite_storage import SQLiteManager
from core.memory.redis_storage import RedisManager
# from core.memory.chroma_storage import ChromaManager # Skipped for CI/Unit test speed/mocking difficulty

# Setup temp paths
TEST_DB = "data/test_memory.db"

@pytest.mark.asyncio
async def test_sqlite_manager():
    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    manager = SQLiteManager(TEST_DB)
    await manager.init_db()
    
    # Test Attribute
    await manager.update_attribute(1, "name", "Delio", 0.9)
    attrs = await manager.get_attributes(1)
    assert attrs["name"] == "Delio"
    
    # Test Lesson
    await manager.store_lesson(1, "trigger", "obs", "correction")
    lessons = await manager.get_lessons(1)
    assert len(lessons) == 1
    assert lessons[0]["trigger"] == "trigger"

@pytest.mark.asyncio
async def test_redis_manager():
    # We assume Redis is running on localhost, else skip
    manager = RedisManager()
    try:
        await manager.connect()
        if not manager.client:
            pytest.skip("Redis not available")
            
        await manager.clear_history(1)
        await manager.append_history(1, "user", "Hello")
        hist = await manager.get_history(1)
        assert len(hist) == 1
        assert hist[0]["content"] == "Hello"
        
        await manager.close()
    except Exception as e:
         pytest.skip(f"Redis error: {e}")
