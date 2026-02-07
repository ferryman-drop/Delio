import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext
from core.state_guard import guard, Action

logger = logging.getLogger("Delio.MemoryWrite")

class MemoryWriteState(BaseState):
    async def execute(self, context: ExecutionContext) -> State:
        await guard.assert_allowed(context.user_id, Action.MEMORY_WRITE)
        try:
            from core.memory.writer import writer
            import core.llm_service as llm
            
            logger.debug(f"💾 Saving memory V2 for user {context.user_id}")
            
            # 1. Short-Term History (Redis) - Async
            # Allows next turn to see this interaction
            await writer.append_history(context.user_id, "user", context.raw_input)
            await writer.append_history(context.user_id, "assistant", context.response, context.metadata.get("model_used"))
            
            # 2. Long-Term Vector (Chroma) - Async
            # Make sure we don't block too long on embeddings if possible, 
            # but writer.save_semantic_memory handles it via threadpool
            await writer.save_semantic_memory(
                context.user_id,
                context.raw_input,
                context.response,
                context.metadata
            )
            
            # 3. Fact Extraction (SQLite)
            # Only run for longer inputs to save tokens/time
            if len(context.raw_input) > 15:
                attributes = await llm.extract_attributes(context.raw_input)
                if attributes:
                    logger.info(f"🧩 Extracted attributes: {attributes}")
                    for key, value in attributes.items():
                        await writer.update_attribute(context.user_id, key, value)

        except Exception as e:
            logger.error(f"❌ Error in MemoryWriteState: {e}")
            context.errors.append(str(e))
            
        return State.IDLE
