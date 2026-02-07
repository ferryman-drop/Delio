
import logging
import json
import re
from states.base import BaseState
from core.state import State
from core.context import ExecutionContext
from core import llm_service

logger = logging.getLogger("Delio.DeepThink")

class DeepThinkState(BaseState):
    def __init__(self, bot=None):
        self.bot = bot

    async def execute(self, context: ExecutionContext) -> State:
        logger.info(f"🧠 Deep Thinking (System 2) for user {context.user_id}")
        
        # UX: Show "Thinking" indicator
        if self.bot:
            try:
                await self.bot.send_chat_action(context.user_id, action="typing")
            except Exception as e:
                logger.warning(f"Failed to send typing action: {e}")

        try:
            # 1. Prepare Memory Summary
            mem = context.memory_context
            mem_summary = self._format_memory_summary(mem)
            
            # 2. Call Deep Think Service
            resp_text, model_used = await llm_service.call_deep_think(
                user_id=context.user_id,
                text=context.raw_input,
                memory_summary=mem_summary,
                image_path=context.metadata.get("image_path")
            )
            
            # 3. Process Response
            # Deep Think usually returns <thought>...</thought> blocks
            context.response = self._cleanup_deep_thought(resp_text)
            context.metadata["model_used"] = f"🧩 {model_used}"
            
            # 4. Check for tool calls (Deep Think can also use tools)
            # We reuse the parser from PlanState if possible or implement here
            from states.plan import PlanState
            plan_instance = PlanState()
            context.tool_calls = plan_instance._extract_tool_calls(resp_text)
            
            return State.DECIDE

        except Exception as e:
            logger.error(f"❌ Deep Think State failure: {e}")
            context.errors.append(f"Deep Think failure: {str(e)}")
            return State.ERROR

    def _format_memory_summary(self, mem: dict) -> str:
        """Condensed summary for Deep Think context."""
        summary = []
        
        # Identity
        identity = mem.get("structured_profile", {}).get("core_identity", {})
        if identity:
             summary.append(f"Identity: {', '.join([f'{k}:{v.get('value')}' for k,v in identity.items()])}")
             
        # Recent Facts
        recent = mem.get("long_term_memories", [])[:3]
        if recent:
             summary.append("Recent Facts: " + " | ".join(recent))
             
        # Lessons
        lessons = mem.get("feedback_signals", [])
        if lessons:
             summary.append("Lessons: " + str(lessons))
             
        return "\n".join(summary)

    def _cleanup_deep_thought(self, text: str) -> str:
        """Removes <thought> blocks for user display, keeping them in logs."""
        # Log the full thought process for debugging
        thought_match = re.search(r"<thought>(.*?)</thought>", text, re.DOTALL)
        if thought_match:
            logger.info(f"💭 Internal Monologue: {thought_match.group(1).strip()[:500]}...")
            
        # Strip the tags for the final response
        clean_text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL).strip()
        
        # If no result outside thought tags, return the whole thing? 
        # (Shouldn't happen with the prompt instruction)
        return clean_text if clean_text else text
