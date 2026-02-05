
import logging
import asyncio
import config
from typing import Tuple, Optional
import os
import json

# Google GenAI SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    # This might fail if using older environment without new SDK, 
    # but requirement Phase 3 specified migrating to it.
    pass

try:
    import anthropic
except ImportError:
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
            logger.warning(f"⚠️ Empty response from {model_name} for user {user_id}")
            return " Error: Empty response from model.", model_name
            
        logger.info(f"🤖 Raw response from {model_name}: {response.text[:1000]}...")
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
        
        # Enforce a strict separator for parsing
        SEPARATOR = "@@@FINAL_RESPONSE@@@"
        
        synergy_prompt = f"""[ACTOR-CRITIC SYNERGY] 
Ти — AID Critic (DeepSeek). Твоя задача — проаналізувати відповідь AID Actor (Gemini).

ПРАВИЛА:
1. Якщо відповідь правильна, логічна та безпечна — поверни статус: "✅ VALIDATED" і саму відповідь без затримок.
2. Якщо є помилки — надай ПОКРАЩЕНУ версію.
3. ФОРМАТ ВИВОДУ (СТРОГО):
   [Твій аналіз/думки тут...]
   {SEPARATOR}
   [Тут лише фінальний текст відповіді для користувача]

4. Якщо відповідь валідна, просто продублюй її після роздільника.
5. НІКОЛИ не надсилай текст до роздільника користувачу.

ІНСТРУКЦІЯ АКТОРУ:
{instruction[:2000]}...

ЗАПИТ КОРИСТУВАЧА:
{user_query}

ВІДПОВІДЬ АКТОРА (Gemini):
{actor_response}

ТВІЙ КРИТИЧНИЙ ВИСНОВОК:"""

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    ds_client.chat.completions.create,
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": synergy_prompt}],
                    temperature=0.3
                ),
                timeout=15.0
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ Critic timeout. Falling back to Actor response.")
            return actor_response, "♊⚠️ (Timeout)"
        
        critic_output = response.choices[0].message.content
        
        # --- ROBUST PARSING PROTOCOL ---
        if SEPARATOR in critic_output:
            final_part = critic_output.split(SEPARATOR)[-1].strip()
            if final_part:
                # If Critic just echoed the actor exactly (validated), keep strict Actor attribution? 
                # Or give credit to Synergistic approach.
                if final_part == actor_response.strip():
                     return final_part, "♊" # Validated, no change
                return final_part, "♊+🐋"
        
        # Fallback for "VALIDATED" without separator (Legacy behavior support)
        if "VALIDATED" in critic_output and len(critic_output) < 200:
             return actor_response, "♊"

        # FAIL-SAFE: If structure is broken, DO NOT return raw output.
        # It risks leaking internal monologue. Return Actor's original.
        logger.warning("⚠️ Critic output format invalid (missing separator). Reverting to Actor to prevent leak.")
        logger.debug(f"Failed Critic Output: {critic_output[:100]}")
        return actor_response, "♊"
        
    except Exception as e:
        logger.warning(f"⚠️ Critic failed: {e}")
        return actor_response, "♊⚠️"

async def call_judge(
    user_query: str,
    actor_response: str,
    instruction: str,
    system_instruction: str = None
) -> Tuple[str, str]:
    """
    Judge logic (Claude 3.5 Sonnet) to refine or arbitrate.
    """
    try:
        if not config.ANTHROPIC_KEY:
            logger.warning("⚠️ Claude API Key missing. Skipping Judge.")
            return actor_response, "♊"

        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_KEY)
        
        prompt = f"""
        CONTEXT: You are the Wise Judge (Claude 3.5 Sonnet).
        GOAL: Review the Actor's response. Ensure it is helpful, accurate, and follows the Persona.
        
        USER QUERY: {user_query}
        
        ACTOR RESPONSE: {actor_response}
        
        SYSTEM INSTRUCTION: {instruction[:1000]}...
        
        YOUR VERDICT:
        - If Good: Return the response as is (or minor polish).
        - If Bad: Rewrite it completely.
        - Return ONLY the final response text. No meta-commentary.
        """
        
        message = await client.messages.create(
            model=config.MODEL_JUDGE,
            max_tokens=1024,
            temperature=0.5,
            system="You are an AI Judge. Return only the refined response.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        judge_output = message.content[0].text
        return judge_output, "♊+🧠" # Brain for Claude
        
    except Exception as e:
        logger.error(f"❌ Judge (Claude) failed: {e}")
        return actor_response, "♊⚠️"

async def evaluate_performance(user_input: str, bot_response: str) -> dict:
    """
    Evaluates the quality of the interaction using a fast model.
    Returns dict: {score: int, critique: str, correction: str}
    """
    try:
        # Use simple Generation for speed
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        prompt = f"""
        ACT AS: AI Quality Assurance Supervisor.
        TASK: Evaluate the following chatbot interaction.
        
        USER INPUT: {user_input}
        BOT RESPONSE: {bot_response}
        
        CRITERIA:
        1. Did it directly answer the intent?
        2. Was the tone appropriate (Helpful, Professional but Friendly)?
        3. Was it concise?
        
        OUTPUT JSON ONLY:
        {{
            "score": <1-10>,
            "critique": "<short text>",
            "correction": "<what to do differently next time>"
        }}
        """
        
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_FAST,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result
        
    except Exception as e:
        logger.warning(f"⚠️ Evaluation failed: {e}")
        return {"score": 5, "critique": "Evaluation Error", "correction": "None"}
