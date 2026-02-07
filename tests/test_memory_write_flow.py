import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.context import ExecutionContext
from core.state import State
from states.memory_write import MemoryWriteState
from core.state_guard import guard

@pytest.mark.asyncio
async def test_memory_write_execution():
    # Setup Context
    ctx = ExecutionContext(user_id=1, event_type="message", raw_input="I live in London", intent="chat")
    ctx.response = "That's a nice city."
    ctx.metadata = {"model_used": "gemini"}
    
    # Mock Writer
    mock_writer = AsyncMock()
    
    # Mock LLM (Attributes)
    mock_llm = AsyncMock()
    mock_llm.extract_attributes.return_value = {"location": "London"}
    
    # Patch dependencies
    with patch('core.memory.writer.writer', mock_writer), \
         patch('core.llm_service.extract_attributes', mock_llm.extract_attributes), \
         patch.object(guard, 'assert_allowed', new_callable=AsyncMock):
         
        state = MemoryWriteState()
        next_state = await state.execute(ctx)
        
        # Verify
        assert next_state == State.IDLE
        
        # 1. Redis History (User + Bot)
        assert mock_writer.append_history.call_count == 2
        mock_writer.append_history.assert_any_call(1, "user", "I live in London")
        
        # 2. Chroma
        mock_writer.save_semantic_memory.assert_awaited_once()
        
        # 3. Attributes
        mock_llm.extract_attributes.assert_awaited_with("I live in London")
        # Check structured memory call
        mock_writer.update_attribute.assert_awaited_with(1, "location", "London")

