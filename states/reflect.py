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
            
        # ACTIVE REFLECTION (Task-012)
        # Only reflect on final responses (no tool outputs pending)
        if context.response and len(context.response) > 10:
            try:
                # 1. Evaluate
                import core.llm_service as llm
                eval_result = await llm.evaluate_performance(context.raw_input, context.response)
                
                score = eval_result.get("score", 10)
                logger.debug(f"🔍 Reflection Score: {score}/10")
                
                # 2. Store if suboptimal
                if score < 7:
                    logger.warning(f"⚠️ Low Performance detected ({score}/10). Learning...")
                    import sqlite3
                    conn = sqlite3.connect('/root/ai_assistant/data/bot_data.db')
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO lessons_learned (user_id, interaction_id, score, critique, correction)
                        VALUES (?, ?, ?, ?, ?)
                    """, (context.user_id, "latest", score, eval_result.get("critique"), eval_result.get("correction")))
                    conn.commit()
                    conn.close()
                else:
                    logger.info("✅ Good cycle (High Perf).")
                    
            except Exception as e:
                logger.error(f"❌ Reflection failed: {e}")

        return State.MEMORY_WRITE
