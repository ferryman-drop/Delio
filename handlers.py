from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging
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
    user_id = message.from_user.id
    core.cache_context(user_id, []) # Reset short-term
    
    # Simple Stats check
    conn = memory_manager.MemoryController().get_connection()
    try:
        row = conn.execute("SELECT SUM(input_tokens + output_tokens), SUM(cost_est) FROM routing_events WHERE user_id=?", (user_id,)).fetchone()
        tokens, cost = row[0] or 0, row[1] or 0.0
    except:
        tokens, cost = 0, 0.0
    finally:
        conn.close()

    # Health Check (simple)
    g_status = "🟢" if config.GEMINI_KEY else "🔴"
    ds_status = "🟢" if config.DEEPSEEK_KEY else "🔴"
    synergy = "✅" if config.ENABLE_SYNERGY else "⏸️"

    msg = f"""👋 *Привіт! Я Delio.*
Твій Life OS Mentor. Допоможу з розкладом, стратегією та фокусом.

*📊 Дашборд:*
• *Моделі:* ♊ Gemini {g_status} | 🐋 DeepSeek {ds_status}
• *Синергія:* {synergy} Actor-Critic
• *Ресурс:* {tokens:,} токенів | ${cost:.4f}

_Що сьогодні робимо? Вибирай команду або просто пиши мені._"""

    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="/interview"), KeyboardButton(text="/memory")],
        [KeyboardButton(text="/logic"), KeyboardButton(text="/start")]
    ], resize_keyboard=True)

    await message.answer(msg, reply_markup=kb, parse_mode="Markdown")

@router.message(Command("next", "далі"))
async def cmd_next(message: types.Message):
    """Trigger the next step in the conversation."""
    user_id = message.from_user.id
    # We treat this as a user message "Continue", but clearer for the bot
    await fsm.handle_event(user_id, "message", "Continue. Provide the next logical step or detail. Do not repeat yourself.")

@router.message(Command("memory"))
async def cmd_memory(message: types.Message):
    """Show detailed memory snapshot."""
    user_id = message.from_user.id
    
    # 1. Get Memory from V2 Controller
    from memory_manager_v2 import init_structured_memory, structured_memory
    
    if not structured_memory:
        import config
        init_structured_memory(config.DB_PATH)
        
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
🔹 */snapshot* - Створити бекап бази даних
🔹 */reset* - Очистити контекст розмови (забути останні 10 повідомлень). Довготривала пам'ять залишається.
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
        import config
        from memory_manager_v2 import init_structured_memory
        init_structured_memory(config.DB_PATH)
        
    snapshot_id = structured_memory.create_snapshot(user_id)
    if snapshot_id:
        await message.answer(f"📸 *Знімок системи створено!*\nID: `{snapshot_id[:8]}`\nСтан вашої пам'яті зафіксовано.", parse_mode="Markdown")
    else:
        await message.answer("❌ Не вдалося створити знімок. Пам'ять порожня або сталася помилка.")

@router.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    
    # Check for Active Interview
    import interviewer
    if interviewer.interviewer_instance.is_active(user_id):
        # Allow only non-commands and explicitly handled commands
        if not message.text.startswith("/") or message.text.lower() in ["/skip", "/cancel"]:
            resp = await interviewer.interviewer_instance.process_answer(user_id, message.text)
            await message.answer(resp, parse_mode="Markdown")
            return

    # Deliver via FSM (Phase 1)
    await fsm.process_event({
        "user_id": user_id,
        "type": "message",
        "text": message.text
    })

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
        
        # Transcribe (Legacy)
        import old_core as legacy_core
        raw_text = await legacy_core.transcribe_audio(temp_filename)
        if not raw_text:
             await message.answer("❌ Не вдалося розпізнати голос.")
             return
             
        # Process Refinement (Legacy)
        refined_text = await legacy_core.refine_text_with_deepseek(raw_text)
        
        # Audio Insight Threshold (Task-013 Zone 2)
        if message.voice.duration >= 30:
            await message.answer(f"📝 *Розпізнано та очищено:*\n\n{refined_text}")
        else:
            logger.info(f"🔇 Voice duration {message.voice.duration}s < 30s. Skipping transcript block.")

        # Deliver via FSM
        await fsm.process_event({
            "user_id": message.from_user.id,
            "type": "voice",
            "text": refined_text
        })
        
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
        
        await fsm.process_event({
            "user_id": message.from_user.id,
            "type": "image",
            "text": f"[IMAGE UPLOAD] {caption}",
            "metadata": {"image_path": temp_filename}
        })
        
        # Note: We rely on FSM or some cleanup job to remove the file?
        # Ideally, we should clean up after processing.
        # But FSM is async. 
        # For Phase 3.3, let's leave it in /tmp or rely on cron cleanup.
        # Or we can delete it after 5 minutes via a task (omitted for brevity).
        
    except Exception as e:
        logger.error(f"Vision Error: {e}")
        await message.answer("❌ Помилка обробки зображення.")

