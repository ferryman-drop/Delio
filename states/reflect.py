import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Reflect")

class ReflectState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # Think about the performance and correctness of the cycle
        logger.debug("🪞 Reflecting on execution cycle...")
        
        if context.errors:
            logger.warning(f"Cycle finished with {len(context.errors)} errors: {context.errors}")
            
        # If we just executed tools, we need to PLAN again to summarize results
        if context.tool_outputs:
            logger.info("📡 Tool outputs found. Routing back to PLAN for integration.")
            return State.PLAN
            
        return State.MEMORY_WRITE
