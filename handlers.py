from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging
import json
import asyncio
import old_core as core
import config
import memory_manager
import old_memory as memory
from core.fsm import instance as fsm
from core.state import State
from states.respond import RespondState

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        user_id = message.from_user.id
        from core.state_guard import guard
        # Acquire session lock before resetting to avoid corrupting active FSM cycle
        session_lock = await fsm._get_session_lock(user_id)
        async with session_lock:
            guard.force_idle(user_id)
        core.cache_context(user_id, []) # Reset short-term legacy
        
        # 1. Active Models Check
        models = []
        if config.GEMINI_KEY:
            models.append("♊ *Gemini 2.0* (Actor)")
        if config.DEEPSEEK_KEY:
            models.append("🐋 *DeepSeek V3* (Critic)")
        if config.ANTHROPIC_KEY:
            models.append("🧠 *Claude 3.5* (Judge)")
        
        models_str = "\n".join([f"  {m}" for m in models])
        
        # 2. Statistics
        conn = memory_manager.MemoryController().get_connection()
        try:
            row = conn.execute("SELECT SUM(input_tokens + output_tokens), SUM(cost_est) FROM routing_events WHERE user_id=?", (user_id,)).fetchone()
            tokens, cost = (row[0] or 0, row[1] or 0.0) if row else (0, 0.0)
        except Exception as e:
            logger.warning(f"Stats query fail: {e}")
            tokens, cost = 0, 0.0
        finally:
            conn.close()

        # 3. System Age (Human Readable)
        from datetime import datetime
        try:
            birth_date = datetime.fromisoformat(config.BIRTH_TIMESTAMP)
            age = datetime.now() - birth_date
            days = age.days
            hours = age.seconds // 3600
            age_display = f"{days} днів {hours} год." if days > 0 else f"{hours} год."
        except:
            age_display = "N/A"

        # 4. Mode Description
        mode_status = "✅ *Active*" if config.ENABLE_SYNERGY else "⏸️ *Paused*"
        mode_desc = "Synergy (♊ + DeepSeek Review)"

        # 5. Build Message
        msg = f"""╔══════════════════╗
   🧬 *DELIO v4.0*
╚══════════════════╝

_Phase 5: Deep Think_

👤 *Асистент:* Life OS Mentor
📆 *Вік Delio:* {age_display}
🧠 *Статус:* 🟢 ONLINE

📊 *Моделі в роботі:*
{models_str}

⚡ *Режим:*
  {mode_status}
  _{mode_desc}_

💰 *Статистика:*
  {tokens:,} токенів  •  ${cost:.4f} est.

_Готовий до роботи. Оберіть команду або пишіть._"""

        kb = ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="/start"), KeyboardButton(text="/interview"), KeyboardButton(text="/logic")],
            [KeyboardButton(text="/define custom")]
        ], resize_keyboard=True)

        await message.answer(msg, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Critical error in cmd_start: {e}")
        await message.answer("❌ Помилка запуску меню. Спробуйте ще раз пізніше.")

@router.message(Command("next", "далі", "more", "ще"))
async def cmd_next(message: types.Message):
    """Trigger the next step in the conversation."""
    user_id = message.from_user.id
    await fsm.process_event({
        "user_id": user_id,
        "type": "message",
        "text": "Continue. Provide the next logical step or detail. Do not repeat yourself."
    })

@router.message(Command("think", "роздуми", "аналіз"))
async def cmd_think(message: types.Message):
    """Explicitly trigger Deep Think mode."""
    user_id = message.from_user.id
    text = message.text.replace("/think", "").strip()
    
    if not text:
        await message.answer("🔍 Введіть запит для глибокого аналізу.\n_Приклад: /think Як мені масштабувати свій бізнес?_")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")
    await fsm.process_event({
        "user_id": user_id,
        "type": "message",
        "text": text,
        "metadata": {"mode": "deep_think"}
    })

@router.message(Command("retry", "щераз", "again", "reload"))
async def cmd_retry(message: types.Message):
    """Retries the last user message."""
    user_id = message.from_user.id
    
    # 1. Fetch last user message from Redis short-term memory
    import config
    from core.memory.redis_storage import RedisManager
    
    # Use config values
    manager = RedisManager(config.REDIS_HOST, config.REDIS_PORT)
    await manager.connect()
    
    try:
        # Get last 5 to be safe
        raw_history = await manager.client.lrange(f"history:{user_id}", -5, -1)
        history = [json.loads(i) for i in raw_history]
        
        # Find last 'user' message
        last_input = None
        for h in reversed(history):
            content = h.get('content', '')
            # Ignore commands (start with /)
            if h.get('role') == 'user' and not content.startswith("/"):
                last_input = content
                break
        
        if not last_input:
            await message.answer("ℹ️ Немає попереднього повідомлення для повтору.")
            return

        await message.answer(f"🔄 *Повторюю запит:* \"{last_input[:50]}...\"", parse_mode="Markdown")
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # 2. Resubmit to FSM in background task to avoid blocking
        asyncio.create_task(fsm.process_event({
            "user_id": user_id,
            "type": "message",
            "text": last_input,
            "metadata": {"is_retry": True}
        }))
        
    except Exception as e:
        logger.error(f"Retry failed: {e}")
        await message.answer("❌ Не вдалося відновити контекст.")
    finally:
        await manager.close()

@router.message(Command("memory"))
async def cmd_memory(message: types.Message):
    """Show detailed memory snapshot."""
    user_id = message.from_user.id
    
    # 1. Get Memory from V2 Controller
    from memory_manager_v2 import init_structured_memory, structured_memory
    
    if not structured_memory:
        init_structured_memory("/root/ai_assistant/data/bot_data.db")

    mem_data = structured_memory.get_all_memory(user_id)
    
    if not mem_data:
        await message.answer("🧠 *Dimensions Empty*\nI haven't learned anything about you yet. Chat with me or use /interview!")
        return
        
    # 2. Format Output
    report = ["🏢 *Delio Structure*"]
    
    # Emoji Map
    EMOJI_MAP = {
        "core_identity": "👤 *Identity*",
        "life_level": "📈 *Life Level*",
        "time_energy": "⏳ *Resource State*",
        "skills_map": "🛠️ *Skills & Tools*",
        "money_model": "💰 *Financial Model*",
        "goals": "🎯 *Active Goals*",
        "decision_patterns": "🧠 *Decision Logic*",
        "behavior_discipline": "⚡ *Habits & Discipline*",
        "trust_communication": "🤝 *Communication Protocol*",
        "feedback_signals": "💡 *Feedback Loop*"
    }
    
    for section, items in mem_data.items():
        if not items:
            continue
            
        header = EMOJI_MAP.get(section, f"📁 *{section.replace('_', ' ').title()}*")
        report.append(f"\n{header}")
        
        for key, data in items.items():
            val = data.get('value', 'N/A')
            conf = data.get('confidence', 0.0)
            
            # Formatting Date Keys (reported_202602012130 -> 01.02.2026)
            key_display = key
            if "reported_" in key:
                try:
                    # simplistic extraction if needed, or just "Запис"
                    key_display = key.replace("reported_", "Запис від ")
                except:
                    key_display = key

            # Formatting Value (Clean Strings)
            if isinstance(val, dict):
                # Flatten dict
                val_str = ", ".join([f"{k}: {v}" for k,v in val.items()])
                val_display = f" `{val_str}`"
            elif isinstance(val, list):
                val_str = "\n  ▪️ ".join([str(v) for v in val])
                val_display = f"\n  ▪️ {val_str}"
            else:
                val_display = f" `{val}`"

            # Confidence Indicator
            stats = ""
            if conf >= 0.8: stats = "✅"
            elif conf >= 0.5: stats = "⚠️"
            else: stats = "❓"

            report.append(f"▪️ *{key_display}* {val_display}")
    
    # Split & Send
    final_text = "\n".join(report)
    if len(final_text) > 4000:
        chunks = [final_text[i:i+4000] for i in range(0, len(final_text), 4000)]
        for chunk in chunks:
            await message.answer(chunk, parse_mode="Markdown")
    else:
        await message.answer(final_text, parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    msg = """*📋 Командний Центр*

🔹 */start* - Перезавантаження Меню
🔹 */logic* - Аналіз останньої відповіді (чому так?)
🔹 */memory* - Перегляд вашої карти пам'яті
🔹 */interview* - Почати інтерв'ю (заповнити прогалини)
🔹 */define* - Створити свою команду (напр. `/define tr Переклади на польську`)
🔹 */snapshot* - Створити бекап бази даних
🔹 */reset* - Очистити контекст розмови.
"""
    await message.answer(msg, parse_mode="Markdown")

@router.message(Command("logic", "agent"))
async def cmd_logic_analysis(message: types.Message):
    """Show details about the last AI response (Meta-Analysis)."""
    user_id = message.from_user.id
    import memory_manager
    conn = memory_manager.MemoryController().get_connection()
    try:
        # Get last routing event
        row = conn.execute("SELECT model_selected, complexity, life_level, cost_est, timestamp FROM routing_events WHERE user_id=? ORDER BY timestamp DESC LIMIT 1", (user_id,)).fetchone()
        
        if row:
            model, comp, level, cost, ts = row
            
            # Status determination
            status = "🟢 Nominal"
            if "Error" in model: status = "🔴 System Fault"
            if "Fallback" in model: status = "🟠 Fallback Mode"
            
            msg = f"""🕵️‍♂️ *Аналіз Агента*
            
*Статус:* {status}
*Час:* `{ts}`

🧠 *Логіка:*
• *Складність:* `{comp}`
• *Рівень життя:* `{level}`
• *Модель:* `{model}`

💸 *Економіка:*
• *Вартість:* `${cost:.6f}`

_Це технічний звіт про те, чому бот обрав саме такий стиль відповіді._"""
        else:
            msg = "🚫 No interaction history found."
            
        await message.answer(msg, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Read Error: {e}")
    finally:
        conn.close()

@router.message(Command("interview"))
async def cmd_interview(message: types.Message):
    """Start interactive memory filling."""
    user_id = message.from_user.id
    import interviewer
    
    msg = await message.answer("🎤 *Interview Protocol Initiated...*")
    try:
        response = await interviewer.interviewer_instance.start_interview(user_id)
        await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Interview Error: {e}")
        await msg.edit_text(f"❌ *Interview Error:* `{e}`", parse_mode="Markdown")

@router.message(Command("cancel", "skip"))
async def cmd_interview_control(message: types.Message):
    """Handle /cancel and /skip during interview."""
    user_id = message.from_user.id
    import interviewer
    if interviewer.interviewer_instance.is_active(user_id):
        resp = await interviewer.interviewer_instance.process_answer(user_id, message.text)
        await message.answer(resp, parse_mode="Markdown")
    else:
        await message.answer("ℹ️ Зараз немає активного інтерв'ю.")

@router.message(Command("snapshot"))
async def cmd_snapshot(message: types.Message):
    """Create a manual memory snapshot."""
    user_id = message.from_user.id
    from memory_manager_v2 import structured_memory
    
    if not structured_memory:
        from memory_manager_v2 import init_structured_memory
        init_structured_memory("/root/ai_assistant/data/bot_data.db")

    snapshot_id = structured_memory.create_snapshot(user_id)
    if snapshot_id:
        await message.answer(f"📸 *Знімок системи створено!*\nID: `{snapshot_id[:8]}`\nСтан вашої пам'яті зафіксовано.", parse_mode="Markdown")
    else:
        await message.answer("❌ Не вдалося створити знімок. Пам'ять порожня або сталася помилка.")

@router.message(Command("define"))
async def cmd_define(message: types.Message):
    """Allow user to define custom commands. Format: /define cmd instruction"""
    user_id = message.from_user.id
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("ℹ️ Використання: `/define слово інструкція`\n_Наприклад: /define tr Переклади це на польську:_")
        return
        
    cmd_name = parts[1].lower().lstrip("/")
    instruction = parts[2]
    
    import sqlite3
    db_path = "/root/ai_assistant/data/bot_data.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT OR REPLACE INTO user_commands (user_id, cmd, instruction) VALUES (?, ?, ?)", (user_id, cmd_name, instruction))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Команда `/{cmd_name}` збережена.\nТепер я буду виконувати: _{instruction}_")
    except Exception as e:
        await message.answer(f"❌ Помилка: {e}")

async def _process_custom_command(user_id: int, text: str) -> tuple[str, dict]:
    """Check for custom commands and return (cleaned_text, metadata)"""
    if not text: return text, {}
    
    cmd_name = None
    payload = text
    
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd_name = parts[0].lower().lstrip("/")
        payload = parts[1] if len(parts) > 1 else ""
    elif text.lower().startswith("команда "):
        parts = text.split(maxsplit=2)
        if len(parts) >= 2:
            cmd_name = parts[1].lower()
            payload = parts[2] if len(parts) > 2 else ""
            
    if cmd_name:
        import sqlite3
        db_path = "/root/ai_assistant/data/bot_data.db"
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute("SELECT instruction FROM user_commands WHERE user_id=? AND cmd=?", (user_id, cmd_name)).fetchone()
            conn.close()
            
            if row:
                instruction = row[0]
                logger.info(f"🚀 Custom Role Activated: /{cmd_name} for user {user_id}")
                return payload, {"custom_role_prompt": instruction, "role_name": cmd_name}
        except:
            pass
            
    return text, {}

@router.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    
    # Check for Active Interview
    import interviewer
    if interviewer.interviewer_instance.is_active(user_id):
        if not message.text.startswith("/") or message.text.lower() in ["/skip", "/cancel"]:
            resp = await interviewer.interviewer_instance.process_answer(user_id, message.text)
            await message.answer(resp, parse_mode="Markdown")
            return

    # 1. Process potential custom command
    text, metadata = await _process_custom_command(user_id, message.text)

    # 2. Deliver via FSM
    await message.bot.send_chat_action(message.chat.id, "typing")
    result = await fsm.process_event({
        "user_id": user_id,
        "type": "message",
        "text": text,
        "metadata": metadata
    })
    
    # Check for critical errors (e.g. timeout) that prevented response
    if result.errors and "Processing timed out" in result.errors:
         await message.answer("⏳ *Час вичерпано.* Я занадто глибоко замислився і не встиг сформувати відповідь. Спробуй ще раз або спрости запит.", parse_mode="Markdown")

    # Legacy call (Keep commented for reference or remove)
    # await core.process_ai_request(message, message.text)

@router.message(F.voice)
async def handle_voice(message: types.Message):
    """
    Handle Voice Messages: Download -> Transcribe (Gemini) -> Clean (DeepSeek) -> Execute
    """
    import os
    import uuid
    
    # Download
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path
    
    temp_filename = f"/tmp/voice_{uuid.uuid4()}.ogg"
    
    try:
        await message.bot.download_file(file_path, temp_filename)
        
        # Transcribe (New Core)
        from core import llm_service
        
        await message.bot.send_chat_action(message.chat.id, "upload_voice")
        raw_text = await llm_service.transcribe_audio(temp_filename)
        
        if not raw_text:
             await message.answer("❌ Не вдалося розпізнати голос.")
             if os.path.exists(temp_filename): os.remove(temp_filename)
             return
             
        # Process Refinement (New Core)
        refined_text = await llm_service.refine_text(raw_text)
        
        # Audio Insight Threshold (Task-013 Zone 2)
        if message.voice.duration >= 30:
            await message.answer(f"📝 *Розпізнано та очищено:*\n\n{refined_text}", parse_mode="Markdown")
        else:
            logger.info(f"🔇 Voice duration {message.voice.duration}s < 30s. Skipping transcript block.")

        # Deliver via FSM
        await message.bot.send_chat_action(message.chat.id, "typing")
        text, metadata = await _process_custom_command(message.from_user.id, refined_text)
        result = await fsm.process_event({
            "user_id": message.from_user.id,
            "type": "voice",
            "text": text,
            "metadata": metadata
        })
        
        if result and result.errors and "Processing timed out" in result.errors:
             await message.answer("⏳ *Час очікування вичерпано.* Я не встиг завершити думку. Спробуй ще раз.")
        
    except Exception as e:
        logger.error(f"Voice Error: {e}")
        await message.answer("❌ Помилка обробки голосового повідомлення.")
    finally:
        # Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@router.message(F.photo)
async def handle_photo(message: types.Message):
    """
    Handle Photo: Download -> FSM (with image_path)
    """
    import os
    import uuid
    
    # 1. Download
    # Get largest photo
    photo = message.photo[-1]
    file_id = photo.file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path
    
    # Ensure dir exists
    os.makedirs("/tmp/vision_buffer", exist_ok=True)
    temp_filename = f"/tmp/vision_buffer/img_{uuid.uuid4()}.jpg"
    
    try:
        await message.bot.download_file(file_path, temp_filename)
        logger.info(f"📸 Image downloaded: {temp_filename}")
        
        # 2. Trigger FSM
        caption = message.caption or ""
        
        # User Feedback
        await message.answer("📸 *Аналізую зображення...*")
        
        result = await fsm.process_event({
            "user_id": message.from_user.id,
            "type": "image",
            "text": f"[IMAGE UPLOAD] {caption}",
            "metadata": {"image_path": temp_filename}
        })

        if result and result.errors and "Processing timed out" in result.errors:
            await message.answer("⏳ *Час очікування вичерпано.* Спробуй ще раз або надішли простіше зображення.", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        await message.answer("❌ Помилка обробки зображення.")

