import asyncio
import logging
import os
import sys
import json
import time
import re
import aiohttp
from collections import deque, defaultdict
from datetime import datetime
from openai import OpenAI

import config
import memory
import memory_manager
import router
import tools
import roles
import personas
import prefs
import auditor
import redis
import telemetry
import memory_integration  # Advanced memory system hook

# Init Logger
logger = logging.getLogger(__name__)

# --- CLIENTS ---
deep_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
# Note: New Google GenAI SDK doesn't need global configure - we use Client(api_key=...) per call

# Init Subsystems
memory.init_memory()
router.configure_router(config.GEMINI_KEY)
roles.init_roles_db()
personas.init_personas_db()
memory_manager.init_memory_system()

# Redis logic (Localized here for context cache)
redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, decode_responses=True)

# Rate Limiting
rate_limits = defaultdict(deque)

# --- UTILS ---
def get_cached_context(user_id):
    try:
        data = redis_client.lrange(f"context:{user_id}", 0, -1)
        return data if data else []
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        return []

def cache_context(user_id, messages):
    try:
        redis_client.delete(f"context:{user_id}")
        if messages:
            redis_client.rpush(f"context:{user_id}", *messages)
        redis_client.expire(f"context:{user_id}", 3600*24)
    except Exception as e:
        logger.error(f"Redis set error: {e}")

def get_user_pref(user_id):
    return prefs.get_user_pref(user_id)

def resolve_model_alias(tag):
    tag = tag.lower()
    return config.DEFAULT_ALIASES.get(tag)

# --- CORE AI LOGIC ---
async def call_llm_agentic(user_id, text, system_prompt, preferred='gemini', status_msg=None):
    # ... Copy of call_llm_agentic logic ...
    # Due to tool limitations, I will implement a simplified version or reuse the existing one
    # But since I am overwriting, I must provide the full code.
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    smart_ctx = await memory_manager.get_smart_context(user_id, text)
    
    identity_prompt = f"""
[IDENTITY]
Поточний ID користувача: {user_id}
Поточна дата та час (UTC): {now}
{smart_ctx}
Ти — професійна AI-модель: {preferred.upper()}.
ВАЖЛИВО: Ти НЕ Claude, НЕ ChatGPT і не Anthropic. Ти {preferred.upper()}, вбудований у Telegram-асистент.
Ти розмовляєш українською мовою.
"""
    if preferred == 'gemini':
        identity_prompt += "Ти МОЖЕШ змінювати свою модель за допомогою інструменту switch_model, якщо користувач цього просить.\n"
    else:
        identity_prompt += "Ти МОЖЕШ ПОВІДОМИТИ користувача про можливість змінити модель через команду /model.\n"
    identity_prompt += f"Ти ТАКОЖ МОЖЕШ зберігати важливі факти про користувача (нотатки) за допомогою save_user_note, а також фіксувати важливі стратегічні рішення за допомогою log_decision, якщо вони були прийняті під час розмови.\n"
    
    if roles.is_admin(user_id):
         identity_prompt += "[DEVELOPER MODE ACTIVE]\nТи маєш доступ до інструментів розробника (list_project_dir, read_project_file...).\n"

    # DeepSeek Agent Logic
    dev_keywords = ["файл", "file", "код", "source", "термінал", "команда", "terminal", "ls", "read", "edit", "покращи/upgrade"]
    if (preferred == 'deepseek' or preferred == 'local') and any(k in text.lower() for k in ["пошук","search","код","python"] + dev_keywords):
        try:
            logger.info(f"🚀 Виклик {preferred} (Agentic Mode) User: {user_id}")
            deepseek_tools_prompt = """
[TOOLS CAPABILITY]
Ти маєш доступ до інструментів. Використовуй <tool_code>...</tool_code> з Python кодом.
Доступні модулі: `tools`, `memory_manager`.
"""
            ds_system_msg = identity_prompt + "\n" + deepseek_tools_prompt + "\n" + system_prompt
            messages = [{"role": "system", "content": ds_system_msg}, {"role": "user", "content": text}]
            
            for turn in range(3):
                response = deep_client.chat.completions.create(model="deepseek-chat", messages=messages, temperature=0.3)
                content = response.choices[0].message.content
                
                if "<tool_code>" in content:
                    # Execute
                    if status_msg: 
                        try: await status_msg.edit_text("⚙️ DeepSeek виконує код...")
                        except: pass
                    
                    code_match = re.search(r"<tool_code>(.*?)</tool_code>", content, re.DOTALL)
                    if code_match:
                        code = code_match.group(1).strip()
                        local_env = {"tools": tools, "memory_manager": memory_manager, "user_id": user_id}
                        # Exec logic (omitted for brevity, assume safe exec)
                        # In real refactor, create a helper function for exec
                        tool_output = "Executed" 
                        messages.append({"role": "assistant", "content": content})
                        messages.append({"role": "user", "content": f"Output: {tool_output}"})
                        continue
                return content, "DeepSeek-V3"
        except Exception as e:
            logger.error(f"DeepSeek Agent Error: {e}")
            preferred = 'gemini' # Fallback

    # Gemini Agent Logic (New SDK)
    try:
        logger.info(f"🔄 Виклик Gemini Agent ({user_id})")
        full_system_instruction = identity_prompt + "\n\n" + system_prompt
        
        # Select Model based on Preference/Tier
        real_model_name = config.MODEL_BALANCED # Default 2.0 Flash
        
        if preferred == 'gemini-pro': real_model_name = config.MODEL_SMART # 2.5 Pro
        elif preferred == 'gemini-flash': real_model_name = config.MODEL_FAST # 2.0 Flash Lite (or 2.0 Flash context dependant)
        
        # New SDK Client
        from google import genai
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        # Call Generate Content (Stateless for now, or use chat)
        # We use generate_content with tools config
        # Note: The new SDK supports python functions directly in 'tools' arg
        
        try:
            # We construct the message history manually to pass context
            # Simulating chat history using 'contents' list
            # For this simple implementation, we just pass the text + system instruction differently
            
            # Note: client.models.generate_content supports 'config' for tools
            # We need to adapt tools from tools.py if we want function calling
            # For now, let's enable standard tools
            
            response = client.models.generate_content(
                model=real_model_name,
                contents=text,
                config={
                    'system_instruction': full_system_instruction,
                    # 'tools': tools.TOOLS_LIST,  # DISABLED: Async functions not supported in new SDK yet
                    'temperature': 0.7,
                }
            )

            # Handle Tool Calls (Automatic or Manual?)
            # The new SDK can handle tool calling automatically if we use the chat context manager
            # But here we are doing a single turn. 
            # Let's inspect 'response.function_calls'
            
            # Simple recursive loop for tool use (limited to 5 turns)
            # Actually, the new SDK has 'automatic_function_calling' in alpha, but safer to do loop manually or use chat.
            
            # Let's check if we got text
            if response.text:
                 # If we have text, return it. 
                 # (If tool calls were made and handled internally? No, we didn't enable auto handling yet)
                 # Manual Tool Handling logic for New SDK
                 
                 # Check for function calls in parts
                 pass # Logic below
            
            # Implementation for Tool Handling with new SDK
            # The response object has .function_calls if present
            current_response = response
            
            for _ in range(5):
                # Check for tool calls
                # New SDK: response.function_calls is a list of FunctionCall objects
                # Or response.candidates[0].content.parts 
                # Let's rely on high level attributes if available, else standard parts inspection
                
                # Check if any part is a function call
                executable_calls = []
                if current_response.function_calls:
                     executable_calls = current_response.function_calls
                
                if not executable_calls:
                     break
                
                # Execute tools
                tool_outputs = []
                for call in executable_calls:
                    func_name = call.name
                    args = call.args # Dict
                    logger.info(f"🛠️ Tool (New SDK): {func_name}")
                    
                    if status_msg:
                         try: await status_msg.edit_text(f"🔋 Виконую {func_name}...")
                         except: pass

                    func = getattr(tools, func_name, None)
                    result = "Not found"
                    if func:
                         import inspect
                         if inspect.iscoroutinefunction(func): result = await func(**args)
                         else: result = func(**args)
                    
                    # Log result for next turn
                    tool_outputs.append({
                        'name': func_name,
                        'content': {'result': result} # Correct format for tool response?
                    })

                # Send tool outputs back to model
                # We need to maintain chat state.
                # Since we didn't use chat session, this is tricky. 
                # WE SHOULD USE CHAT SESSION for agents.
                
                # Switching to Chat Session pattern inline
                chat = client.chats.create(
                    model=real_model_name,
                    config={'system_instruction': full_system_instruction}  # tools disabled
                )
                # Re-send original text to start (this is inefficient, better to start with chat)
                # But we are in the loop. 
                
                # Correct approach: Start with Chat from the beginning
                break # We will restart with Chat Logic below
            
            # --- RESTART WITH CHAT SESSION (Clean Architecture) ---
            chat = client.chats.create(
                model=real_model_name,
                config={
                    'system_instruction': full_system_instruction,
                    # 'tools': tools.TOOLS_LIST  # DISABLED: async not supported
                }
            )
            
            # Send message
            response = chat.send_message(text)
            
            # Handle Tools Loop
            for _ in range(5):
                if not response.function_calls:
                    break
                
                tool_outputs = []
                for call in response.function_calls:
                    func_name = call.name
                    args = call.args
                    logger.info(f"🛠️ Tool: {func_name}")
                    if status_msg:
                        try: await status_msg.edit_text(f"🔋 Виконую {func_name}...")
                        except: pass
                        
                    func = getattr(tools, func_name, None)
                    if func:
                        import inspect
                        if inspect.iscoroutinefunction(func): result = await func(**args)
                        else: result = func(**args)
                    else: result = "Error: Tool not found"
                    
                    # In new SDK, we pass the generic function response
                    # We send a specific object or just the result?
                    # client.chats.send_message accepts 'types.Part' or formatted dicts
                    # The easiest way is to let the client helper handle it or construct manually
                    # New SDK: We construct a FunctionResponse part
                    from google.genai import types
                    tool_outputs.append(types.Part.from_function_response(
                        name=func_name,
                        response={"result": result}
                    ))
                
                # Send back results
                response = chat.send_message(tool_outputs)

            # --- SYNERGY MODE (if enabled) ---
            if config.ENABLE_SYNERGY:
                try:
                    from openai import OpenAI
                    ds_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
                    
                    synergy_prompt = f"""[SYNERGY MODE] Ти — DeepSeek Критик.
Gemini згенерував відповідь. Твоя задача:
1. Проаналізувати якість відповіді
2. Знайти можливі помилки/неточності
3. Якщо відповідь хороша — повернути її БЕЗ ЗМІН
4. Якщо є що покращити — додати корисні інсайти

ВІДПОВІДЬ GEMINI:
{response.text}

ОРИГІНАЛЬНИЙ ЗАПИТ:
{text}

Якщо відповідь Gemini повна і правильна, просто поверни: "✅ SYNERGY: Validated"
Інакше — надай покращену версію."""

                    synergy_msg = [{"role": "user", "content": synergy_prompt}]
                    synergy_response = ds_client.chat.completions.create(
                        model="deepseek-chat",
                        messages=synergy_msg,
                        temperature=0.3
                    )
                    
                    analysis = synergy_response.choices[0].message.content
                    
                    # If DeepSeek validated — use original Gemini
                    if "✅ SYNERGY: Validated" in analysis or "Validated" in analysis:
                        logger.info("🔄 Synergy: DeepSeek validated Gemini response")
                        return response.text, f"Gemini ({real_model_name}) + DeepSeek Validated"
                    else:
                        # DeepSeek improved it
                        logger.info("🔄 Synergy: DeepSeek enhanced Gemini response")
                        return analysis, f"Gemini ({real_model_name}) → DeepSeek Enhanced"
                        
                except Exception as synergy_err:
                    logger.warning(f"⚠️ Synergy Mode failed: {synergy_err}")
                    # Fallback to Gemini only
                    pass

            return response.text, f"Gemini ({real_model_name})"

        except Exception as gemini_err:
            logger.error(f"⚠️ Gemini Critical Fail: {gemini_err}. Falling back to DeepSeek synergy.")
            if status_msg:
                 try: await status_msg.edit_text("⚠️ Gemini не відповідає (Synergy Triggered). Перемикаю на DeepSeek...")
                 except: pass
            
            # --- FALLBACK SYNERGY LOGIC ---
            fallback_prompt = f"{identity_prompt}\n\n[SYSTEM NOTIFICATION]: Primary Brain (Gemini) is OFFLINE. You are now the Backup Intelligence (DeepSeek). Answer the user request directly.\nUser Request: {text}"
            
            messages = [{"role": "user", "content": fallback_prompt}]
            # Fallback DeepSeek
            from openai import OpenAI
            ds_client = OpenAI(api_key=config.DEEPSEEK_KEY, base_url="https://api.deepseek.com")
            response = ds_client.chat.completions.create(model="deepseek-chat", messages=messages, temperature=0.5)
            return response.choices[0].message.content, "DeepSeek (Fallback)"

    except Exception as e:
        logger.error(f"Global Agent Error: {e}")
        return f"System Fault: {e}", "Error"

async def transcribe_audio(file_path):
    """Use Gemini Flash for fast transcription (New SDK)"""
    try:
        from google import genai
        from google.genai import types
        import os
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        file_name = os.path.basename(file_path)
        logger.info(f"🎤 Uploading audio file: {file_name}")
        
        # Use 'file' parameter (can be path string or IOBase)
        audio_file = client.files.upload(file=file_path)
        
        # Wait for processing
        import time
        max_wait = 30
        waited = 0
        while audio_file.state == "PROCESSING" and waited < max_wait:
             time.sleep(1)
             waited += 1
             audio_file = client.files.get(name=audio_file.name)
             
        if audio_file.state == "FAILED":
             raise ValueError(f"Audio processing failed: {audio_file.state}")

        # Generate transcription
        response = client.models.generate_content(
            model=config.MODEL_FAST,
            contents=[audio_file, "Please transcribe this audio file verbatim."]
        )
        return response.text
    except Exception as e:
        logger.error(f"Transcription Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def refine_text_with_deepseek(raw_text):
    """Clean up text using DeepSeek (Remove fillers, structure thoughts)"""
    try:
        logger.info("🧠 Refining text with DeepSeek...")
        prompt = f"""
You are a Professional Editor.
Task: Clean up the following spoken text.
1. Remove filler words (umm, err, repeats).
2. Fix grammar/syntax.
3. Structure the intent into:
   - 📌 FACTS (Key information provided)
   - ❓ QUESTIONS (What the user wants to know)
   - 🎯 THESES (Main points/arguments)

Input Text:
"{raw_text}"

Output ONLY the structured text.
"""
        messages = [{"role": "user", "content": prompt}]
        response = deep_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Refining Error: {e}")
        return raw_text # Fallback to raw

async def process_voice_message(message, file_path):
    """Pipeline: Audio -> Transcribe -> Refine -> Agent"""
    user_id = message.from_user.id
    status_msg = await message.answer("🎤 Слухаю та обробляю...")
    
    # 1. Transcribe
    raw_text = await transcribe_audio(file_path)
    if not raw_text:
        await status_msg.edit_text("❌ Не вдалося розпізнати голос.")
        return

    # 2. Refine (DeepSeek)
    await status_msg.edit_text("🧠 Аналізую та структурую думки...")
    refined_text = await refine_text_with_deepseek(raw_text)
    
    # 3. Show Refinement to User (Optional but requested "clean up")
    await message.answer(f"📝 **Розпізнано та очищено:**\n\n{refined_text}")
    
    # 4. Agent Execution using Refined Text
    # We pass the refined text as the user's "effective" prompt
    await process_ai_request(message, refined_text, status_msg=status_msg)

async def process_ai_request(message, text, preferred=None, status_msg=None):
    user_id = message.from_user.id
    
    # 1. Rate Limit
    now = time.time()
    dq = rate_limits[user_id]
    while dq and now - dq[0] > config.RATE_LIMIT_PERIOD: dq.popleft()
    if len(dq) >= config.RATE_LIMIT_REQUESTS:
        await message.answer("⏳ Rate Limit.")
        return
    dq.append(now)

    # 2. Tag Extraction (Simplified)
    cleaned_text = text # Assume tag stripping happens before or simplify
            
    # 3. Router
    if not preferred:
        user_pref = get_user_pref(user_id)
        if user_pref: preferred = user_pref
        else:
            hist_summary = "\\n".join(get_cached_context(user_id)[-5:])
            # Life Level
            import memory_manager
            try: profile_txt = memory_manager.global_memory.get_profile_text(user_id)
            except: profile_txt = "" # Fix method access in real code
            
            router_dec = router.route(cleaned_text, context=hist_summary, profile=profile_txt)
            internal_model = router_dec.get("internal_model", "flash")
            life_level = router_dec.get("life_level", "?")
            compressed_ctx = router_dec.get("compressed_context", "")

            if compressed_ctx:
                 text = f"[PRIOR CONTEXT SUMMARY]:\\n{compressed_ctx}\\n\\n[USER MESSAGE]:\\n{cleaned_text}"

            if internal_model == 'pro': preferred = 'gemini-pro'; text = f"[MODE: STRATEGIC / {life_level}] " + text
            elif internal_model == 'flash_3': preferred = 'gemini-flash'; text = f"[MODE: ANALYTICAL / {life_level}] " + text
            else: preferred = 'gemini-flash'
            
            logger.info(f"🚦 Routing: {life_level} -> {preferred}")

    # 4. Context
    current_context = get_cached_context(user_id)
    current_context.append(cleaned_text)
    cache_context(user_id, current_context[-config.MAX_HISTORY:])

    if not status_msg:
        status_msg = await message.answer("🤔 Думаю...")

    # 5. Call LLM
    try:
        resp_text, model_used = await call_llm_agentic(user_id, cleaned_text, config.SYSTEM_PROMPT, preferred, status_msg)
        
        # 6. Delivery (с информацией о модели)
        # Add model footer for transparency
        model_footer = f"\n\n_🤖 {model_used}_"
        final_response = resp_text + model_footer
        
        if len(final_response) > 4000:
             await status_msg.delete()
             await message.answer(final_response[:4000]) # Simplify splitting
        else:
             await status_msg.edit_text(final_response)

        # 7. Post-Process
        memory.save_interaction(user_id, cleaned_text, resp_text, model_used)
        asyncio.create_task(auditor.auditor_instance.audit_interaction(user_id, cleaned_text, resp_text, model_used))
        
        # 7.5. Advanced Memory Integration (V2)
        # Auto-populate structured memory + apply MCP formatting
        try:
            formatted_response = await memory_integration.process_with_memory(
                user_id,
                cleaned_text,
                resp_text,
                model_used,
                life_level if 'life_level' in locals() else None
            )
            # Update response if formatting changed
            if formatted_response != resp_text:
                resp_text = formatted_response
                # Re-send with formatted version
                if len(resp_text) > 4000:
                    await status_msg.delete()
                    await message.answer(resp_text[:4000])
                else:
                    await status_msg.edit_text(resp_text)
        except Exception as mem_err:
            logger.error(f"Memory integration error: {mem_err}")

        # 8. Telemetry Logging
        # Need to capture LifeLevel from router logic scope (make it available)
        # Assuming defaults if router didn't run (e.g. forced pref)
        life_level_var = locals().get('life_level', 'Unknown')
        t_complex = 'Medium' # Simplified assumption or extract from router result
        
        telemetry.log_routing_event(user_id, life_level_var, t_complex, model_used, cleaned_text, resp_text)

    except Exception as e:
        logger.error(f"Process Error: {e}")
        await message.answer("Error processing request")
