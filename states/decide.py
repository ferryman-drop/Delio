import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Decide")

class DecideState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # Determine if we should Act or Respond
        # For now, if it's a heartbeat, we might ACT.
        # If it's a message, we RESPOND.
        
        if context.event_type == "heartbeat":
            logger.info("🤖 Autonomy trigger detected in DECIDE")
            return State.ACT
            
        return State.RESPOND
