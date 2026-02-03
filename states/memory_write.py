import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.MemoryWrite")

class MemoryWriteState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        guard.assert_allowed(context.user_id, Action.MEMORY_WRITE)
        try:
            # Wrap legacy memory saving
            import old_memory as legacy_memory
            
            logger.debug(f"💾 Saving memory for user {context.user_id}")
            
            legacy_memory.save_interaction(
                user_id=context.user_id,
                user_input=context.raw_input,
                bot_response=context.response,
                model_used=context.metadata.get("model_used", "AID")
            )
            
            # Note: memory_integration.process_with_memory (V2) 
            import memory_integration
            await memory_integration.process_with_memory(
                user_id=context.user_id,
                user_message=context.raw_input,
                ai_response=context.response,
                model_used=context.metadata.get("model_used", "AID"),
                life_level=context.metadata.get("life_level", None)
            )
            
        except Exception as e:
            logger.error(f"❌ Error in MemoryWriteState: {e}")
            context.errors.append(str(e))
            
        return State.IDLE
