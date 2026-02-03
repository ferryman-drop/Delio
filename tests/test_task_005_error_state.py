import pytest
from unittest.mock import AsyncMock, Mock
from core.context import ExecutionContext
from core.state import State
from states.error import ErrorState

@pytest.mark.asyncio
async def test_error_state_critic_message():
    """
    Test that ErrorState sends the specific critic message when 'Critic rejected' is in errors.
    """
    mock_bot = AsyncMock()
    error_state = ErrorState(bot=mock_bot)
    
    context = ExecutionContext(user_id=123, event_type="message", raw_input="test")
    # Simulate the error string added by PlanState
    context.errors.append("Critic rejected the response (Potential Safety/Logic Issue)")
    
    next_state = await error_state.execute(context)
    
    assert next_state == State.IDLE
    
    # Check what message was sent
    mock_bot.send_message.assert_awaited_once()
    args, _ = mock_bot.send_message.call_args
    sent_text = args[1]
    
    assert "система безпеки (Critic) заблокувала" in sent_text

@pytest.mark.asyncio
async def test_error_state_generic_message():
    """
    Test that ErrorState sends a generic message for other errors.
    """
    mock_bot = AsyncMock()
    error_state = ErrorState(bot=mock_bot)
    
    context = ExecutionContext(user_id=456, event_type="message", raw_input="test")
    context.errors.append("Some random API failure")
    
    await error_state.execute(context)
    
    args, _ = mock_bot.send_message.call_args
    sent_text = args[1]
    
    assert "внутрішня помилка" in sent_text
