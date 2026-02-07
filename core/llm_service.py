
import logging
import asyncio
import config
from typing import Tuple, Optional
import os
import json

# Google GenAI SDK (required)
try:
    from google import genai
    from google.genai import types
except ImportError as _e:
    raise ImportError(f"google-genai SDK is required: {_e}. Install with: pip install google-genai")

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger("Delio.LLMService")


async def _retry_async(coro_fn, max_retries=2, base_delay=1.0):
    """Simple retry with exponential backoff for LLM calls."""
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_fn()
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"⚠️ LLM call failed (attempt {attempt+1}/{max_retries+1}): {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
    raise last_err


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
        _uploaded_file_name = None

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
                        await asyncio.sleep(1)
                        uploaded_file = client.files.get(name=uploaded_file.name)
                        
                    contents.append(uploaded_file)
                    _uploaded_file_name = uploaded_file.name

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
        
        response = await _retry_async(lambda: asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        ))
        
        if not response.text:
            logger.warning(f"⚠️ Empty response from {model_name} for user {user_id}")
            return " Error: Empty response from model.", model_name
            
        # Cleanup uploaded file to avoid quota exhaustion
        if _uploaded_file_name:
            try:
                client.files.delete(name=_uploaded_file_name)
            except Exception:
                pass

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
        prompt = f"""ACT AS: AI Quality Assurance Supervisor.
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
        # Use DeepSeek (Critic) to avoid self-evaluation bias (Actor is Gemini)
        if config.DEEPSEEK_KEY:
            try:
                from openai import OpenAI
                ds_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
                response = await asyncio.to_thread(
                    ds_client.chat.completions.create,
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                result = json.loads(response.choices[0].message.content)
                if isinstance(result, list) and len(result) > 0:
                    return result[0]
                return result
            except Exception as ds_err:
                logger.warning(f"⚠️ DeepSeek evaluation failed, falling back to Gemini: {ds_err}")

        # Fallback to Gemini
        client = genai.Client(api_key=config.GEMINI_KEY)
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
        return None  # Caller must handle None (skip lesson storage)

# Add to core/llm_service.py


async def transcribe_audio(file_path: str) -> Optional[str]:
    """
    Transcribes audio file using Gemini Flash (Fast).
    """
    try:
        from google import genai
        from google.genai import types
        import os
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        file_name = os.path.basename(file_path)
        logger.info(f"🎤 Uploading audio file: {file_name}")
        
        if not os.path.exists(file_path):
             logger.error(f"❌ Audio file not found: {file_path}")
             return None
             
        # Upload
        audio_file = client.files.upload(file=file_path)
        
        # Wait for processing
        max_wait = 30
        waited = 0
        while audio_file.state == "PROCESSING" and waited < max_wait:
             await asyncio.sleep(1)
             waited += 1
             audio_file = client.files.get(name=audio_file.name)
             
        if audio_file.state == "FAILED":
             raise ValueError(f"Audio processing failed: {audio_file.state}")

        # Generate transcription
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_FAST,
            contents=[audio_file, "Please transcribe this audio file verbatim. If the audio is in Ukrainian, Russian, or Polish, transcribe it exactly in that language. Do not translate. Return ONLY the text."]
        )
        return response.text
    except Exception as e:
        logger.error(f"Transcription Error: {e}")
        return None

async def refine_text(raw_text: str) -> str:
    """
    Clean up text using DeepSeek (Preferred) or Gemini (Fallback).
    Removes fillers, structures thoughts.
    """
    try:
        logger.info("🧠 Refining text...")
        
        prompt = f"""
You are a Professional Editor.
Task: Clean up the following spoken text.
1. Remove filler words (umm, err, repeats).
2. Fix grammar/syntax.
3. Keep the original language (Ukrainian).
4. Output ONLY the refined text. No introductory phrases.

Input Text:
"{raw_text}"
"""
        # Try DeepSeek first (cheaper/better for text logic)
        if config.DEEPSEEK_KEY:
            try:
                from openai import OpenAI
                ds_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
                response = await asyncio.to_thread(
                    ds_client.chat.completions.create,
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                return response.choices[0].message.content
            except Exception as ds_err:
                logger.warning(f"DeepSeek refine failed: {ds_err}. Falling back to Gemini.")
        
        # Fallback to Gemini
        client = genai.Client(api_key=config.GEMINI_KEY)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_FAST,
            contents=prompt
        )
        return response.text
        
    except Exception as e:
        logger.error(f"Refining Error: {e}")
        return raw_text # Fallback to raw

async def extract_attributes(text: str) -> dict:
    """
    Витягує атрибути користувача з тексту (ім'я, місто, професія тощо).
    Повертає dict {key: value} або {}.
    """
    try:
        client = genai.Client(api_key=config.GEMINI_KEY)
        prompt = f"""Extract personal attributes from this text. Return JSON only.
Keys should be lowercase English (e.g. "name", "city", "profession", "age", "language").
If no attributes found, return empty object {{}}.

Text: "{text}"
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
        if isinstance(result, dict):
            return result
        return {}
    except Exception as e:
        logger.warning(f"⚠️ extract_attributes failed: {e}")
        return {}


async def call_deep_think(
    user_id: int,
    text: str,
    memory_summary: str,
    image_path: Optional[str] = None
) -> Tuple[str, str]:
    """
    System 2 Reasoning: Slower, deeper, analytical.
    Uses Pro model and specialized instructions.
    """
    try:
        from core.prompts.deep_think import DEEP_THINK_SYSTEM
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        # Build analytical context
        full_instruction = f"{DEEP_THINK_SYSTEM}\n\n### [CONTEXT SUMMARY]\n{memory_summary}"
        
        logger.info(f"🧩 Initiating Deep Think (System 2) for user {user_id}")
        
        # Prepare contents
        contents = []
        if image_path and os.path.exists(image_path):
            uploaded_file = client.files.upload(file=image_path)
            # Wait for processing
            while uploaded_file.state == "PROCESSING":
                await asyncio.sleep(1)
                uploaded_file = client.files.get(name=uploaded_file.name)
            contents.append(uploaded_file)

        contents.append(f"[QUERY]: {text}")
        
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_SMART, # Always use Pro for Deep Think
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=full_instruction,
                temperature=0.4, # Lower temperature for better logic
                max_output_tokens=2048
            )
        )
        
        if not response.text:
             return "Error: Empty response in Deep Think", "Error"
             
        return response.text, config.MODEL_SMART
        
    except Exception as e:
        logger.error(f"❌ Deep Think Error: {e}")
        raise e
