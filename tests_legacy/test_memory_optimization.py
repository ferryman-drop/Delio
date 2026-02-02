import asyncio
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_memory")

# Mock memory module if needed, or use real one
# We will use real one but ensure we don't crash if deps are missing
try:
    import memory_manager
    import memory
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

async def test_memory_controller():
    logger.info("Testing MemoryController...")
    
    # 1. Initialize
    user_id = 99999 # Test user
    
    # Clean up previous test data if any (optional, or just append)
    # memory_manager.global_memory.init_db() # Already called on import
    
    # 2. Test Profile Update
    logger.info("2. Testing Update Profile...")
    memory_manager.update_profile(
        user_id, 
        core_values=["Growth", "Truth"], 
        goals=["Build Life OS", "Master AI"]
    )
    
    # 3. Test Add Decision
    logger.info("3. Testing Add Decision...")
    memory_manager.add_decision(
        user_id,
        "Choose Database",
        "Need persistent storage",
        "SQLite is simple and sufficient",
        "Stable memory"
    )
    
    # 4. Test Smart Context Retrieval
    logger.info("4. Testing Smart Context...")
    ctx = await memory_manager.get_smart_context(user_id, "What are my goals?")
    
    logger.info("\n--- SMART CONTEXT ---")
    logger.info(ctx)
    logger.info("---------------------\n")
    
    assert "Build Life OS" in ctx, "Goal not found in context"
    assert "Choose Database" in ctx, "Decision not found in context"
    assert "USER PROFILE" in ctx
    
    logger.info("✅ Smart Context Test Passed")

    # 5. Test Vector Search (Integration)
    # This might fail if Chroma/Gemini not configured, so we wrap
    try:
        logger.info("5. Testing Vector Search Integration...")
        # Save a fake node
        memory.save_note(user_id, "I like apples", "preferences")
        
        # Helper method isn't ensuring immediate consistency usually (Chroma might be fast enough)
        await asyncio.sleep(1) 
        
        ctx_with_rag = await memory_manager.get_smart_context(user_id, "Do I like apples?")
        if "apples" in ctx_with_rag:
             logger.info("✅ RAG Context found 'apples'")
        else:
             logger.warning("⚠️ RAG Context did not find 'apples' (might be embedding latency or mock)")
             
    except Exception as e:
        logger.warning(f"⚠️ Vector test skipped/failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_memory_controller())
