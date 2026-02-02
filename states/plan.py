import logging
import config
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Plan")

class PlanState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # For Phase 1, we wrap legacy call_llm_agentic
        import core as legacy_core
        
        logger.debug(f"🤔 Planning for user {context.user_id}")
        
        try:
            # We call the legacy function. 
            # Note: call_llm_agentic returns (resp_text, model_used)
            resp_text, model_used = await legacy_core.call_llm_agentic(
                user_id=context.user_id,
                text=context.raw_input,
                system_prompt=config.SYSTEM_PROMPT,
                preferred='gemini' # Default for now
            )
            
            context.response = resp_text
            context.metadata["model_used"] = model_used
            
            return State.RESPOND
            
        except Exception as e:
            logger.exception(f"❌ Error in PlanState: {e}")
            context.errors.append(str(e))
            return State.IDLE
