import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Decide")

class DecideState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        # Determine if we should Act or Respond
        
        # 1. Check for explicit tool calls from PLAN
        if context.tool_calls:
            logger.info(f"🛠️ Tool calls detected ({len(context.tool_calls)}). Routing to ACT.")
            return State.ACT

        # 2. Check for heartbeat/background triggers
        if context.event_type == "heartbeat":
            # If model said SKIP (or variations like "SKIP." or "Skip"), go IDLE.
            resp_text = context.response or ""
            resp_clean = resp_text.strip().upper()

            # STRICT FILTER: Any response starting with SKIP is a SKIP.
            # Covers "SKIP", "SKIP: No changes", "SKIP.", leading markdown, etc.
            if resp_clean.lstrip("*_#>- ").startswith("SKIP"):
                logger.info(f"🤐 Heartbeat SKIPPED for user {context.user_id}")
                return State.IDLE
            
            logger.info("🤖 Autonomy trigger detected in DECIDE (Active Message)")
            return State.RESPOND
            
        return State.RESPOND
