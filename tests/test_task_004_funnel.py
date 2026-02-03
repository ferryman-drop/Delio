import asyncio
import pytest
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# 1. Setup global mocks for modules
# We create them here so we can reference them in tests
mock_redis_module = MagicMock()
mock_vector_module = MagicMock()
mock_structured_module = MagicMock()

sys_modules_mock = {
    'legacy': MagicMock(),
    'legacy.old_memory': mock_vector_module,
    'legacy.memory_manager': mock_redis_module,
    'legacy.memory_manager_v2': mock_structured_module,
    'old_memory': mock_vector_module,
    'memory_manager': mock_redis_module,
    'memory_manager_v2': mock_structured_module,
}

# Apply patch to sys.modules for the whole module
# (Keep sys.modules patch to avoid real imports during initial load)
with patch.dict('sys.modules', sys_modules_mock):
    # Import AFTER patching
    import core.memory.funnel as funnel_module
    from core.memory.funnel import funnel
    from core.state_guard import guard, Action

# Inject mocks directly into the module to ensure they are used
funnel_module.redis_db = mock_redis_module
funnel_module.vector_db = mock_vector_module
funnel_module.structured_db = mock_structured_module

@pytest.mark.asyncio
async def test_funnel_aggregation():
    # Reset mocks
    mock_redis_module.reset_mock()
    mock_vector_module.reset_mock()
    mock_structured_module.reset_mock()
    
    # Configure Mocks
    mock_redis_module.get_history.return_value = [{"role":"user", "content":"hi"}] * 15
    mock_redis_module.get_history.side_effect = None # Reset side effect
    
    # Vector
    mock_vector_module.search_memories = AsyncMock(return_value=["Memory 1", "Memory 2"])
    # Ensure sync method doesn't exist to force async path
    del mock_vector_module.search_memory
    
    # Structured
    mock_structured_module.structured_memory.get_all_memory.return_value = {"profile": "User"}
    
    # Run
    with patch.object(guard, 'assert_allowed', new_callable=AsyncMock) as mock_guard:
        result = await funnel.aggregate_context(1, "Q")
        
        mock_guard.assert_awaited_with(1, Action.MEM_RETRIEVE)
        assert len(result["short_term"]) == 10
        assert result["long_term_memories"] == ["Memory 1", "Memory 2"]

@pytest.mark.asyncio
async def test_funnel_graceful_failure():
    # Reset
    mock_redis_module.reset_mock()
    
    # FAIL Redis
    mock_redis_module.get_history.side_effect = Exception("Redis Down")
    
    # Configure Vector to works (so we don't crash there)
    mock_vector_module.search_memories = AsyncMock(return_value=[])
    
    # Run
    with patch.object(guard, 'assert_allowed', new_callable=AsyncMock):
        result = await funnel.aggregate_context(1, "Q")
        
        # Redis failed -> empty list
        assert result["short_term"] == []
        # Vector worked -> empty list (as configured)
        assert result["long_term_memories"] == []
