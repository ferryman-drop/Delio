import logging
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext

logger = logging.getLogger("Delio.Reflect")

class ReflectState(BaseState):
    def __init__(self, bot):
        self.bot = bot

    async def execute(self, context: ExecutionContext) -> State:
        # Think about the performance and correctness of the cycle
        logger.debug("🪞 Reflecting on execution cycle...")
        
        if context.errors:
            logger.warning(f"Cycle finished with {len(context.errors)} errors: {context.errors}")
            
        # If we just executed tools, we need to PLAN again to summarize results
        if context.tool_outputs:
            logger.info("📡 Tool outputs found. Routing back to PLAN for integration.")
            return State.PLAN
            
        # ACTIVE REFLECTION (Task-012)
        # Only reflect on final responses (no tool outputs pending)
        if context.response and len(context.response) > 10:
            try:
                # 1. Evaluate
                import core.llm_service as llm
                eval_result = await llm.evaluate_performance(context.raw_input, context.response)

                if not eval_result:
                    logger.warning("⚠️ Evaluation returned None (API failure). Skipping reflection.")
                else:
                    score = eval_result.get("score", 10)
                    logger.debug(f"🔍 Reflection Score: {score}/10")

                    # 2. Handle Optimistic Correction (Phase 2)
                    if score < 5 and context.metadata.get("message_id"):
                        msg_id = context.metadata.get("message_id")
                        correction = eval_result.get("correction", "Вибач, я виявив помилку у своїй попередній відповіді.")

                        logger.warning(f"🔥 Catastrophic Error Detected ({score}/10). Correcting message {msg_id}...")

                        warning_text = f"⚠️ *КОРЕКЦІЯ ТА ПОПЕРЕДЖЕННЯ*\n\n{correction}\n\n_Попередня відповідь була видалена або змінена через низьку достовірність._"

                        await self.bot.edit_message_text(
                            text=warning_text,
                            chat_id=context.user_id,
                            message_id=msg_id,
                            parse_mode="Markdown"
                        )

                    # 3. Store lessons
                    if score < 7:
                        logger.warning(f"⚠️ Low Performance detected ({score}/10). Learning...")
                        from core.memory.writer import writer
                        await writer.save_lesson(
                            user_id=context.user_id,
                            trigger="observation_low_score",
                            observation=eval_result.get("critique", "No critique"),
                            correction=eval_result.get("correction", "No correction")
                        )
                    else:
                        logger.info("✅ Good cycle (High Perf).")

            except Exception as e:
                logger.error(f"❌ Reflection failed: {e}")

        # 4. Heartbeat Digestion (Context Summarization)
        if context.event_type == "heartbeat":
            try:
                from core.memory.digest import summarize_recent_history
                # Digestion extracts facts from recent 20 messages
                await summarize_recent_history(context.user_id)
            except Exception as e:
                logger.error(f"❌ Digestion during reflection failed: {e}")

        return State.MEMORY_WRITE
