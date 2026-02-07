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
        try:
            if not context.response:
                logger.warning("⚠️ No response to send in RESPOND")
                return State.ERROR
                
            # Deliver response to Telegram (user_id is the chat_id)
            await guard.assert_allowed(context.user_id, Action.NETWORK)
            
            # 1. Silhouette Signature Logic (Task-013)
            # Ensure metadata exists and model_used is string
            model_tag = str(context.metadata.get('model_used', 'AID')).lower()
            if "claude" in model_tag or "🧠" in model_tag: signature = "🧠"
            elif "gemini" in model_tag or "☂️" in model_tag: signature = "☂️"
            elif "deepseek" in model_tag or "🐋" in model_tag: signature = "🐋"
            elif "⌛" in model_tag or "timeout" in model_tag: signature = "⌛"
            else: signature = "☂️" # Default to Gemini (main actor)

            raw_response = str(context.response)
            
            # Strip leaks (Zone 1)
            leaks = ["Критичний висновок:", "Critical Conclusion:", "✅ VALIDATED"]
            for leak in leaks:
                raw_response = raw_response.replace(leak, "")
            
            # 2. Adaptive Fragmentation Logic
            is_command = context.raw_input.startswith("/")
            is_short = len(raw_response) < 800
            is_simple = context.intent in ["GREETING", "UTILITY"]

            if is_command or is_short or is_simple:
                chunks = [raw_response.strip()]
                logger.info(f"⚡ Skipping fragmentation for UX (is_command={is_command}, is_short={is_short}, is_simple={is_simple})")
            else:
                # Split by double newlines to find logical "Thoughts"
                chunks = [c.strip() for c in raw_response.split("\n\n") if c.strip()]
            
            if not chunks:
                chunks = [raw_response.strip()]

            logger.info(f"📤 Sending response to {context.user_id} ({len(chunks)} chunks)")

            sent_fragments = []
            max_retries = 3
            for i, chunk in enumerate(chunks):
                # Signature goes ONLY on the last chunk
                final_chunk = chunk
                if i == len(chunks) - 1:
                    final_chunk = f"{chunk}\n\n{signature}"
                
                sent_fragments.append(final_chunk)
                message_id = context.metadata.get("message_id")

                # Retry loop for each chunk
                sent = False
                for attempt in range(max_retries):
                    try:
                        if i == 0 and message_id:
                            # Use edit for the first fragment if it's a response to a telegram message
                            try:
                                 await self.bot.edit_message_text(final_chunk, context.user_id, message_id, parse_mode="Markdown")
                            except Exception as m_error:
                                 logger.warning(f"Markdown edit failed: {m_error}. Fallback to plain text.")
                                 await self.bot.edit_message_text(final_chunk, context.user_id, message_id)
                        else:
                            try:
                                 await self.bot.send_message(context.user_id, final_chunk, parse_mode="Markdown")
                            except Exception as m_error:
                                 logger.warning(f"Markdown send failed: {m_error}. Fallback to plain text.")
                                 await self.bot.send_message(context.user_id, final_chunk)
                        sent = True
                        break
                    except Exception as e:
                        logger.error(f"❌ Attempt {attempt+1} failed for chunk {i+1}: {e}")
                        # If edit fails (e.g. message_id invalid), try sending anew
                        if i == 0 and message_id:
                            try:
                                await self.bot.send_message(context.user_id, final_chunk, parse_mode="Markdown")
                                sent = True
                                break
                            except: pass
                        await asyncio.sleep(2)
                
                if not sent:
                    context.sent_response = "\n\n".join(sent_fragments)
                    logger.error("❌ Failed to send response chunk after retries.")
                    return State.ERROR

                # Delay between fragments (simulating thought)
                if i < len(chunks) - 1:
                    delay = 2 if i == 0 else 1.5
                    await asyncio.sleep(delay)
            
            context.sent_response = "\n\n".join(sent_fragments)
            return State.REFLECT

        except Exception as e:
            logger.exception(f"💥 Critical Error in RespondState: {e}")
            context.errors.append(f"RespondState Crisis: {str(e)}")
            return State.ERROR
