import asyncio
import logging
from aiogram import Bot, Dispatcher
import config
import handlers
import scheduler
# Import subsystems to ensure init runs if not imported elsewhere
import core 

# Setup Logging (already done in config.py)
logger = logging.getLogger("LifeOS")

async def main():
    import os
    logger.info(f"🚀 Starting Life OS Assistant (PID: {os.getpid()})...")
    
    # Init Bot
    bot = Bot(token=config.TG_TOKEN)
    dp = Dispatcher()
    
    # Register Routers
    dp.include_router(handlers.router)
    
    # Init Scheduler
    scheduler.init_scheduler(bot)
    
    # Init Advanced Memory System (V2)
    import memory_manager_v2 as mm2
    import memory_populator
    import model_control
    
    db_path = "/root/ai_assistant/data/bot_data.db"
    structured_memory = mm2.init_structured_memory(db_path)
    memory_populator.init_memory_populator(structured_memory)
    model_control.init_model_controller(structured_memory)
    logger.info("✅ Advanced Memory System (V2) initialized")
    
    # Set Bot Commands (Menu)
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="🏠 Головна / Перезапуск"),
        BotCommand(command="agent", description="🕵️ Аналіз останньої відповіді"),
        BotCommand(command="memory", description="🧠 Моя Пам'ять (V2)"),
        BotCommand(command="snapshot", description="📸 Знімок пам'яті"),
        BotCommand(command="help", description="❓ Допомога"),
        BotCommand(command="reset", description="🧹 Очистити контекст"),
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
