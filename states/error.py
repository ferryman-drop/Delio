import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Error")

class ErrorState(BaseState):
    def __init__(self, bot=None):
        self.bot = bot

    async def execute(self, context: ExecutionContext) -> State:
        logger.error(f"🚨 Handling ERROR state for user {context.user_id}")
        logger.error(f"Errors: {context.errors}")
        
        # 1. Notify user if possible
        if self.bot and context.user_id:
            try:
                error_msg = "⚠️ Вибачте, сталася внутрішня помилка. Мій розробник вже працює над цим."
                
                # If we have specific safe error messages, we can use them
                is_critic_rejection = any("Critic rejected" in str(e) for e in context.errors)
                if is_critic_rejection:
                    error_msg = "⚠️ Моя внутрішня система безпеки (Critic) заблокувала цю відповідь. Спробуйте перефразувати."
                
                await self.bot.send_message(context.user_id, error_msg)
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")
        
        # 2. Reset / Cleanup ??
        # The FSM loop terminates when ERROR -> IDLE?
        # Standard flow is usually ERROR -> IDLE
        
        return State.IDLE
