
import logging
import asyncio
import config
from typing import Tuple, Optional
import os

# Google GenAI SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    # This might fail if using older environment without new SDK, 
    # but requirement Phase 3 specified migrating to it.
    pass

logger = logging.getLogger("Delio.LLMService")

async def call_actor(
    user_id: int,
    text: str,
    system_instruction: str,
    preferred_model: str = "gemini",
    image_path: Optional[str] = None
) -> Tuple[str, str]:
    """
    Primary Actor logic. 
    Supports Image input -> Gemini.
    Text input -> Gemini (or generic fallback).
    """
    try:
        # Determine real model name based on alias/preference
        model_name = config.MODEL_BALANCED # default
        
        if "pro" in preferred_model: model_name = config.MODEL_SMART
        elif "flash" in preferred_model: model_name = config.MODEL_FAST
        
        logger.info(f"🎤 Calling Actor ({model_name}). Image: {image_path is not None}")
        
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        # Prepare content list
        contents = []
        
        # 1. Image (if present)
        if image_path:
            if not os.path.exists(image_path):
                logger.warning(f"❌ Image path not found: {image_path}")
            else:
                logger.debug(f"📤 Uploading image: {image_path}")
                try:
                    # Upload to GenAI File API (for temporal use)
                    # Note: We could also pass bytes directly if supported, 
                    # but File API is better for larger files or context caching.
                    # For simple single-turn, passing PIL image or bytes is often faster/easier 
                    # but new SDK prefers types.Part or File object.
                    
                    # Method A: Client File API
                    uploaded_file = client.files.upload(file=image_path)
                    
                    # Wait for processing if video (images are usually instant)
                    # But safer to check
                    if uploaded_file.state == "PROCESSING":
                        import time
                        time.sleep(1) 
                        uploaded_file = client.files.get(name=uploaded_file.name)
                        
                    contents.append(uploaded_file)
                    
                except Exception as up_err:
                    logger.error(f"Image upload failed: {up_err}")
                    # Fallback? Maybe skip image.
        
        # 2. Text
        if text:
            contents.append(text)
            
        if not contents:
            # Should not happen in normal flow
            return "Error: Empty input", "Error"

        # 3. Call Generate
        # We assume stateless call (generate_content) for now, as context history 
        # is baked into 'system_instruction' or 'contents' by the caller if needed.
        # However, FSM 'PlanState' passes history in 'system_instruction' as text summary?
        # Ideally, we should pass history as actual chat history messages.
        # But for Phase 3.3 Task 007, we stick to the interface: user_raw_input + system_instruction.
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        
        if not response.text:
            return " Error: Empty response from model.", model_name
            
        return response.text, model_name

    except Exception as e:
        logger.error(f"❌ Actor Error: {e}")
        # Fallback to text-only if image failed? or DeepSeek?
        # For now, propagate error
        raise e


async def call_critic(
    user_query: str,
    actor_response: str,
    instruction: str
) -> Tuple[str, str]:
    """
    Critic logic (DeepSeek) to validate Actor response.
    """
    try:
        # Lazy import openai
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
{instruction[:2000]}... (truncated)

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
            if not clean_resp or len(clean_resp) < 5: # If it was just the label
                return actor_response, "♊"
            return clean_resp, "♊+🐋"
            
        return critic_output, "♊+🐋 (Corrected)"
        
    except Exception as e:
        logger.warning(f"⚠️ Critic failed: {e}")
        return actor_response, "♊⚠️"
