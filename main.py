import asyncio
import logging
from aiogram import Bot, Dispatcher
import sys
import os

# Add legacy path to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'legacy'))

import config
import handlers
import scheduler
from core import tools # Registered agent tools
# Import subsystems to ensure init runs
import core 

import core.logger
# Setup Logging
logger = core.logger.setup_logging("logs/delio_trace.json", level=config.LOG_LEVEL)

async def main():
    import os
    logger.info(f"🚀 Starting Delio Assistant (PID: {os.getpid()})...")
    
    # Init Bot
    bot = Bot(token=config.TG_TOKEN)
    dp = Dispatcher()
    
    # Register Routers
    dp.include_router(handlers.router)
    
    # Init Scheduler
    scheduler.init_scheduler(bot)
    
    # Init FSM Infrastructure
    from core.fsm import instance as fsm
    from core.state import State
    from states.observe import ObserveState
    from states.retrieve import RetrieveState
    from states.plan import PlanState
    from states.deep_think import DeepThinkState
    from states.decide import DecideState
    from states.act import ActState
    from states.respond import RespondState
    from states.reflect import ReflectState
    from states.memory_write import MemoryWriteState
    from states.error import ErrorState

    fsm.register_handler(State.OBSERVE, ObserveState())
    fsm.register_handler(State.RETRIEVE, RetrieveState())
    fsm.register_handler(State.PLAN, PlanState(bot))
    fsm.register_handler(State.DEEP_THINK, DeepThinkState(bot))
    fsm.register_handler(State.DECIDE, DecideState())
    fsm.register_handler(State.ACT, ActState())
    fsm.register_handler(State.RESPOND, RespondState(bot))
    fsm.register_handler(State.REFLECT, ReflectState(bot))
    fsm.register_handler(State.MEMORY_WRITE, MemoryWriteState())
    fsm.register_handler(State.ERROR, ErrorState(bot))
    logger.info("✅ AID Kernel (FSM) initialized")

    # Init Advanced Memory System (V2)
    import memory_manager_v2 as mm2
    import memory_populator
    import model_control
    
    db_path = "/root/ai_assistant/data/bot_data.db"
    structured_memory = mm2.init_structured_memory(db_path)
    memory_populator.init_memory_populator(structured_memory)
    model_control.init_model_controller(structured_memory)
    logger.info("✅ Advanced Memory System (V2) initialized")
    
    # Register Bot for Critical Alerts (Task-014)
    from core.state_guard import guard
    guard.set_bot(bot)
    
    # Set Bot Commands (Menu)
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="🏠 Головна / Перезапуск"),
        BotCommand(command="define", description="📝 Створити команду"),
        BotCommand(command="interview", description="🎤 Інтерв'ю"),
        BotCommand(command="memory", description="🧠 Моя Пам'ять (V2)"),
        BotCommand(command="logic", description="🕵️ Логіка відповіді"),
        BotCommand(command="think", description="🧠 Глибокий аналіз (System 2)"),
        BotCommand(command="profilemaster", description="👑 Режим Стратега"),
        BotCommand(command="profiletextboost", description="✍️ Режим Редактора"),
        BotCommand(command="word", description="🌐 Перекладач"),
        BotCommand(command="uptext", description="🚀 Покращення тексту"),
        BotCommand(command="snapshot", description="📸 Знімок пам'яті"),
        BotCommand(command="reset", description="🧹 Очистити контекст"),
        BotCommand(command="help", description="❓ Допомога"),
    ]
    await bot.set_my_commands(commands)
    
    # Start
    try:
        logger.info("✅ Bot is running...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Critical Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot stopped.")
