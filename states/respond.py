import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Respond")

class RespondState(BaseState):
    def __init__(self, bot):
        self.bot = bot

    async def execute(self, context: ExecutionContext) -> State:
        if not context.response:
            logger.warning("⚠️ No response to send in RESPOND")
            return State.IDLE
            
        # Deliver response to Telegram (user_id is the chat_id)
        try:
            # We add the model information footer as in legacy process_ai_request
            model_footer = f"\n\n_🤖 {context.metadata.get('model_used', 'AID')}_"
            final_response = context.response + model_footer
            
            # Simple chunking if needed (legacy limit 4000)
            if len(final_response) > 4000:
                await self.bot.send_message(context.user_id, final_response[:4000])
            else:
                await self.bot.send_message(context.user_id, final_response)
                
            logger.info(f"📤 Response sent to user {context.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send response: {e}")
            context.errors.append(str(e))
            
        # Transitions to REFLECT or MEMORY_WRITE
        return State.MEMORY_WRITE
