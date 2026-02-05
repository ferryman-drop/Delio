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
        
        # 1. Silhouette Signature Logic (Task-013)
        model_tag = context.metadata.get('model_used', 'AID').lower()
        if "claude" in model_tag or "🧠" in model_tag: signature = "🧠"
        elif "gemini" in model_tag or "☂️" in model_tag: signature = "☂️"
        elif "deepseek" in model_tag or "🐋" in model_tag: signature = "🐋"
        elif "⌛" in model_tag or "timeout" in model_tag: signature = "⌛"
        else: signature = "☂️" # Default to Gemini (main actor)

        raw_response = context.response
        
        # Strip leaks (Zone 1)
        leaks = ["Критичний висновок:", "Critical Conclusion:", "✅ VALIDATED"]
        for leak in leaks:
            raw_response = raw_response.replace(leak, "")
        
        # 2. Fragmentation Logic (Task-013)
        # Split by double newlines to find logical "Thoughts"
        chunks = [c.strip() for c in raw_response.split("\n\n") if c.strip()]
        
        if not chunks:
            chunks = [raw_response.strip()]

        logger.info(f"📤 Sending fragmented response to {context.user_id} ({len(chunks)} chunks)")

        max_retries = 3
        for i, chunk in enumerate(chunks):
            # Signature goes ONLY on the last chunk
            final_chunk = chunk
            if i == len(chunks) - 1:
                final_chunk = f"{chunk}\n\n{signature}"

            # Retry loop for each chunk
            sent = False
            for attempt in range(max_retries):
                try:
                    await self.bot.send_message(context.user_id, final_chunk)
                    sent = True
                    break
                except Exception as e:
                    logger.error(f"❌ Attempt {attempt+1} failed for chunk {i+1}: {e}")
                    await asyncio.sleep(2)
            
            if not sent:
                return State.ERROR

            # Delay between fragments (simulating thought) - Zone 3
            if i < len(chunks) - 1:
                delay = 3 if i == 0 else 2
                await asyncio.sleep(delay)
        
        return State.REFLECT
