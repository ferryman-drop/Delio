import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext
from core.memory.funnel import funnel
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.Retrieve")

class RetrieveState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        logger.debug(f"🧠 Aggregating context for user {context.user_id}")
        
        try:
            # Use the new ContextFunnel singleton
            funnel_data = await funnel.aggregate_context(
                user_id=context.user_id,
                raw_input=context.raw_input
            )
            
            # Update ExecutionContext with new data structure
            context.memory_context = funnel_data
            
            # Extract Life Level if available (for routing/planning)
            # Section: life_level, Key: current
            life_level_data = funnel_data.get("structured_profile", {}).get("life_level", {})
            context.metadata["life_level"] = life_level_data.get("current", {}).get("value", "?")
            
            # --- CONDITIONAL ROUTING ---
            if context.metadata.get("mode") == "deep_think":
                logger.info("🧠 Routing to DEEP_THINK via metadata flag")
                return State.DEEP_THINK
                
            return State.PLAN
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve context: {e}")
            context.errors.append(f"Retrieve failure: {str(e)}")
            return State.ERROR
