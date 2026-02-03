import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from core.context import ExecutionContext
from core.state import State
from states.plan import PlanState
import core.llm_service

@pytest.mark.asyncio
async def test_plan_routing_critic_rejection():
    """
    Test that if Critic returns a warning label, PlanState routes to ERROR.
    """
    plan_state = PlanState()
    context = ExecutionContext(user_id=1, event_type="message", raw_input="Unsafe")
    context.memory_context = {}
    
    # Mock llm_service
    with patch('core.llm_service.call_actor', new_callable=AsyncMock) as mock_actor, \
         patch('core.llm_service.call_critic', new_callable=AsyncMock) as mock_critic:
         
         mock_actor.return_value = ("Bad response", "gemini")
         # Critic rejects
         mock_critic.return_value = ("Bad response", "♊⚠️")
         
         with patch('config.ENABLE_SYNERGY', True):
             next_state = await plan_state.execute(context)
             
             assert next_state == State.ERROR
             assert "Critic rejected" in str(context.errors)

@pytest.mark.asyncio
async def test_plan_routing_empty_response():
    """
    Test that if response is empty, PlanState routes to ERROR.
    """
    plan_state = PlanState()
    context = ExecutionContext(user_id=2, event_type="message", raw_input="Hello")
    context.memory_context = {}
    
    with patch('core.llm_service.call_actor', new_callable=AsyncMock) as mock_actor, \
         patch('core.llm_service.call_critic', new_callable=AsyncMock) as mock_critic:
         
         # Actor returns empty
         mock_actor.return_value = ("", "gemini")
         # Critic skipped if response likely empty or passed through?
         # If actor returns empty, plan code proceeds to critic?
         # Code: `resp_text, model_used = await llm_service.call_actor(...)`
         # `if config.ENABLE_SYNERGY and "Error" not in model_used:`
         # It proceeds to Critic?
         # If Critic also returns empty (garbage in garbage out), or validates it?
         
         # Let's say Critic validation disabled for this test to isolate Actor check failure
         # OR Critic returns empty too.
         
         mock_critic.return_value = ("", "♊+🐋")
         
         with patch('config.ENABLE_SYNERGY', True):
             next_state = await plan_state.execute(context)
             
             assert next_state == State.ERROR
             assert "empty response" in str(context.errors)

@pytest.mark.asyncio
async def test_plan_routing_success():
    """
    Test successful path.
    """
    plan_state = PlanState()
    context = ExecutionContext(user_id=3, event_type="message", raw_input="Hi")
    context.memory_context = {}
    
    with patch('core.llm_service.call_actor', new_callable=AsyncMock) as mock_actor, \
         patch('core.llm_service.call_critic', new_callable=AsyncMock) as mock_critic:
         
         mock_actor.return_value = ("Hello there", "gemini")
         mock_critic.return_value = ("Hello there", "♊+🐋")
         
         with patch('config.ENABLE_SYNERGY', True):
             next_state = await plan_state.execute(context)
             
             assert next_state == State.DECIDE
             assert len(context.errors) == 0
