import logging
import asyncio
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.Respond")

class RespondState(BaseState):
    def __init__(self, bot):
        self.bot = bot

    async def execute(self, context: ExecutionContext) -> State:
        if not context.response:
            logger.warning("⚠️ No response to send in RESPOND")
            return State.ERROR
            
        # Deliver response to Telegram (user_id is the chat_id)
        await guard.assert_allowed(context.user_id, Action.NETWORK)
        
        footer = context.metadata.get('model_used', 'AID')
        final_response = f"{context.response}\n\n_{footer}_"
        logger.info(f"📤 Preparing to send response to {context.user_id} (Length: {len(final_response)})")
        logger.debug(f"Content: {final_response[:200]}...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Simple chunking if needed (legacy limit 4000)
                if len(final_response) > 4000:
                    await self.bot.send_message(context.user_id, final_response[:4000])
                else:
                    await self.bot.send_message(context.user_id, final_response)
                    
                logger.info(f"✅ Response sent to user {context.user_id} (Attempt {attempt+1})")
                return State.REFLECT
                
            except Exception as e:
                logger.error(f"❌ Attempt {attempt+1} failed to send response: {e}")
                if attempt == max_retries - 1:
                    context.errors.append(f"Final delivery failure: {str(e)}")
                else:
                    await asyncio.sleep(1) # Wait before retry
        
        # If we reach here, it failed all retries
        return State.ERROR
