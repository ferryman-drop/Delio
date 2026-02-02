from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging
import core
import config
import memory_manager
import memory
from core.fsm import FSMController
from core.state import State
from states.observe import ObserveState
from states.retrieve import RetrieveState
from states.plan import PlanState
from states.respond import RespondState
from states.memory_write import MemoryWriteState

router = Router()
logger = logging.getLogger(__name__)

# Initialize FSM (Single instance for the router)
fsm = FSMController()
fsm.register_handler(State.OBSERVE, ObserveState())
fsm.register_handler(State.RETRIEVE, RetrieveState())
fsm.register_handler(State.PLAN, PlanState())
# RESPOND needs bot, will be set per request or use a wrapper
fsm.register_handler(State.MEMORY_WRITE, MemoryWriteState())

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    # Reset context
    core.cache_context(user_id, [])
    
    # Get Telemetry Stats
    import sqlite3
    conn = memory_manager.MemoryController().get_connection()
    try:
        # Sum tokens and cost for this user
        row = conn.execute("SELECT SUM(input_tokens), SUM(output_tokens), SUM(cost_est) FROM routing_events WHERE user_id=?", (user_id,)).fetchone()
        in_tok, out_tok, cost = row
        in_tok = in_tok or 0
        out_tok = out_tok or 0
        cost = cost or 0.0
    except:
        in_tok, out_tok, cost = 0, 0, 0.0
    conn.close()

    # Check if synergy mode is enabled
    import config
    synergy_status = "🔄 Активна" if config.ENABLE_SYNERGY else "⏸️ Вимкнена"
    
    msg = f"""🤖 Delio Assistant v3.0 — Ваш AI стратег

🧠 AI Stack:
 • Gemini 2.0 Flash — швидкість + reasoning
 • Gemini 2.5 Pro — складні стратегії (автовибір)
 • DeepSeek V3 — критичний аналіз
 • Режим синергії: {synergy_status}
 • Adaptive Routing — автоматичний вибір моделі за Life Level

📊 Ваша статистика:
 • Токенів опрацьовано: {in_tok + out_tok:,}
 • Вартість: ${cost:.5f}
 • ID: {user_id}

✨ Можливості:
🗣️ Голосові повідомлення — транскрипція + аналіз Gemini
🧠 Memory V2 — структурована пам'ять (Life Map, Goals, Contexts)
🎯 Interview Mode — Time/Energy профайл
🕵️ Agent Analysis (/agent) — глибокий розбір відповідей
📸 Snapshot — моментальний знімок пам'яті
💬 Smart Context — компресія історії діалогу
🔄 Auto Model Selection — Flash для простих, Pro для складних задач

🎛️ Команди:
 • /logic — режим аналізу Logic
 • /memory — подивитись пам'ять V2
 • /interview — заповнити профіль
 • /agent — аналіз останньої відповіді
 • /snapshot — знімок стану
 • /reset — очистити контекст

👇 Панель керування:"""

    # Keyboard
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="/logic"), KeyboardButton(text="/memory")],
        [KeyboardButton(text="/interview"), KeyboardButton(text="/start")]
    ], resize_keyboard=True)

    await message.answer(msg, reply_markup=kb)

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
        await message.answer("🧠 **Dimensions Empty**\nI haven't learned anything about you yet. Chat with me or use /interview!")
        return
        
    # 2. Format Output
    report = ["🏢 **Delio Structure**"]
    
    # Emoji Map
    EMOJI_MAP = {
        "core_identity": "👤 **Identity**",
        "life_level": "📈 **Life Level**",
        "time_energy": "⏳ **Resource State**",
        "skills_map": "🛠️ **Skills & Tools**",
        "money_model": "💰 **Financial Model**",
        "goals": "🎯 **Active Goals**",
        "decision_patterns": "🧠 **Decision Logic**",
        "behavior_discipline": "⚡ **Habits & Discipline**",
        "trust_communication": "🤝 **Communication Protocol**",
        "feedback_signals": "💡 **Feedback Loop**"
    }
    
    for section, items in mem_data.items():
        if not items:
            continue
            
        header = EMOJI_MAP.get(section, f"📁 **{section.title()}**")
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
    msg = """**📋 Командний Центр**

🔹 **/start** - Перезавантаження Меню
🔹 **/logic** - Аналіз останньої відповіді (чому так?)
🔹 **/memory** - Перегляд вашої карти пам'яті
🔹 **/interview** - Почати інтерв'ю (заповнити прогалини)
🔹 **/snapshot** - Створити бекап бази даних
🔹 **/reset** - Очистити контекст розмови (забути останні 10 повідомлень). Довготривала пам'ять залишається.
"""
    await message.answer(msg, parse_mode="Markdown")

@router.message(Command("logic"))
async def cmd_agent(message: types.Message):
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
            
            msg = f"""🕵️‍♂️ **Аналіз Агента**
            
**Статус:** {status}
**Час:** `{ts}`

🧠 **Логіка:**
• **Складність:** `{comp}`
• **Рівень життя:** `{level}`
• **Модель:** `{model}`

💸 **Економіка:**
• **Вартість:** `${cost:.6f}`

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
    
    msg = await message.answer("🎤 **Interview Protocol Initiated...**")
    try:
        response = await interviewer.interviewer_instance.start_interview(user_id)
        await msg.edit_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Interview Error: {e}")
        await msg.edit_text(f"❌ **Interview Error:** `{e}`", parse_mode="Markdown")

@router.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    
    # Check for Active Interview
    import interviewer
    if interviewer.interviewer_instance.is_active(user_id):
        # Process answer intercept
        resp = await interviewer.interviewer_instance.process_answer(user_id, message.text)
        await message.answer(resp)  # No markdown parsing to avoid errors
        return

    # Deliver via FSM (Phase 1)
    fsm.register_handler(State.RESPOND, RespondState(message.bot))
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
        import core as legacy_core
        raw_text = await legacy_core.transcribe_audio(temp_filename)
        if not raw_text:
             await message.answer("❌ Не вдалося розпізнати голос.")
             return
             
        # Process Refinement (Legacy)
        refined_text = await legacy_core.refine_text_with_deepseek(raw_text)
        await message.answer(f"📝 **Розпізнано та очищено:**\n\n{refined_text}")

        # Deliver via FSM
        fsm.register_handler(State.RESPOND, RespondState(message.bot))
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
    # Vision logic
    await message.answer("📸 Фото в процесі перенесення.")
