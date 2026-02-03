import logging
import asyncio
import config
from typing import Tuple, Optional

# Temporary import until full migration
# We assume legacy/old_core.py exists. 
# If 'legacy' is a package, we can import from it.
try:
    from legacy import old_core as legacy_core
except ImportError:
    try:
        import old_core as legacy_core
    except ImportError:
        import sys
        import os
        # Fallback: try adding legacy to path
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../legacy')))
        import old_core as legacy_core

logger = logging.getLogger("Delio.LLMService")

async def call_actor(
    user_id: int,
    text: str,
    system_instruction: str,
    preferred_model: str = "gemini"
) -> Tuple[str, str]:
    """
    Викликає Actor модель (Gemini/DeepSeek) через легасі ядро (поки що).
    Returns: (response_text, model_label)
    """
    try:
        # Wrapping legacy call
        resp_text, model_used = await legacy_core.call_llm_agentic(
            user_id=user_id,
            text=text,
            system_prompt=system_instruction,
            preferred=preferred_model
        )
        return resp_text, model_used
    except Exception as e:
        logger.error(f"LLM Actor failed: {e}")
        raise

async def call_critic(
    user_query: str,
    actor_response: str,
    instruction: str
) -> Tuple[str, str]:
    """
    Викликає Critic модель (DeepSeek) для валідації.
    """
    try:
        # We perform lazy import of OpenAI to avoid overhead if not used/installed in other envs
        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("Optional dependency 'openai' not found. Skipping Critic phase.")
            return actor_response, "♊"

        ds_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        
        synergy_prompt = f"""[ACTOR-CRITIC SYNERGY] 
Ти — AID Critic (DeepSeek). Твоя задача — проаналізувати відповідь AID Actor (Gemini).

ПРАВИЛА:
1. Якщо відповідь правильна, логічна та безпечна — поверни статус: "✅ VALIDATED" і саму відповідь без затримок.
2. Якщо є помилки, логічні прогалини або відхилення від інструкцій — надай ТІЛЬКИ покращену версію відповіді.
3. Звертай увагу на точність фактів та відповідність Life Level користувача.

ІНСТРУКЦІЯ АКТОРУ:
{instruction[:500]}... (truncated)

{config.TELEGRAM_STYLE}

ЗАПИТ КОРИСТУВАЧА:
{user_query}

ВІДПОВІДЬ АКТОРА (Gemini):
{actor_response}

ТВІЙ КРИТИЧНИЙ ВИСНОВОК:"""

        response = await asyncio.to_thread(
            ds_client.chat.completions.create,
            model="deepseek-chat",
            messages=[{"role": "user", "content": synergy_prompt}],
            temperature=0.3
        )
        
        critic_output = response.choices[0].message.content
        
        if "✅ VALIDATED" in critic_output or "VALIDATED" in critic_output:
            # Clean up the label from response if it leaked
            clean_resp = critic_output.replace("✅ VALIDATED", "").replace("VALIDATED", "").strip()
            if not clean_resp: # If it was just the label
                return actor_response, "♊"
            return clean_resp, "♊+🐋"
            
        return critic_output, "♊+🐋 (Corrected)"
        
    except Exception as e:
        logger.warning(f"⚠️ Critic failed: {e}")
        return actor_response, "♊⚠️"
