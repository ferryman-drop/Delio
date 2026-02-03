import pytest
import json
from unittest.mock import AsyncMock, patch
from core.context import ExecutionContext
from core.state import State
from states.plan import PlanState
from states.decide import DecideState
from states.act import ActState
from states.reflect import ReflectState
from core.tool_registry import registry
from core import tools # Trigger registration

@pytest.mark.asyncio
async def test_autonomous_tool_flow():
    """
    Verifies the flow from PLAN -> DECIDE -> ACT -> REFLECT -> PLAN.
    """
    user_id = 123
    plan_state = PlanState()
    decide_state = DecideState()
    act_state = ActState()
    reflect_state = ReflectState()
    
    # Context initialization
    context = ExecutionContext(user_id=user_id, raw_input="What time is it?")
    context.memory_context = {}
    
    # 1. PLAN - Mock Actor to return a tool call
    with patch('core.llm_service.call_actor', new_callable=AsyncMock) as mock_actor:
        # LLM returns JSON tool call
        mock_actor.return_value = (
            "Thinking: I need to check the time.\n```json\n{\"tool_calls\": [{\"name\": \"get_time\", \"arguments\": {}}]}\n```",
            "gemini"
        )
        # Mock Critic to just pass through
        with patch('config.ENABLE_SYNERGY', False):
            next_state = await plan_state.execute(context)
            
            assert next_state == State.DECIDE
            assert len(context.tool_calls) == 1
            assert context.tool_calls[0]["name"] == "get_time"
            assert "Thinking" in context.response # Cleaned text
            assert "json" not in context.response # JSON removed

    # 2. DECIDE - Verify routing to ACT
    next_state = await decide_state.execute(context)
    assert next_state == State.ACT

    # 3. ACT - Verify tool execution
    # Ensure get_time is registered (it should be via tools/__init__.py if loaded, but let's be safe)
    # Actually, we can just check registry or register a dummy if needed.
    
    with patch.object(registry.get_tool("get_time"), 'execute', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "2026-02-03T22:30:00"
        
        next_state = await act_state.execute(context)
        
        assert next_state == State.REFLECT
        assert len(context.tool_outputs) == 1
        assert context.tool_outputs[0]["output"] == "2026-02-03T22:30:00"

    # 4. REFLECT - Verify routing back to PLAN
    next_state = await reflect_state.execute(context)
    assert next_state == State.PLAN

    # 5. PLAN (Second pass) - Verify injection of tool output
    with patch('core.llm_service.call_actor', new_callable=AsyncMock) as mock_actor:
        # Mocking the call to see the system prompt
        # We need to capture the system_instruction passed to call_actor
        
        await plan_state.execute(context)
        
        # Check the last call to mock_actor
        args, kwargs = mock_actor.call_args
        system_instruction = kwargs.get('system_instruction')
        
        assert "РЕЗУЛЬТАТИ ВИКОНАННЯ ІНСТРУМЕНТІВ" in system_instruction
        assert "2026-02-03T22:30:00" in system_instruction
        # Check that tool_calls were cleared in PlanState (as per code)
        assert context.tool_calls == []
