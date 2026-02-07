import asyncio
import logging
import sys
import os

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from aiogram import Bot, Dispatcher
from client import handlers

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Delio.Client")

async def main():
    logger.info("📡 Starting Delio Client...")
    
    # Init Bot
    bot = Bot(token=config.TG_TOKEN)
    dp = Dispatcher()
    
    # Register Routers
    dp.include_router(handlers.router)
    
    # Start
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Client connected to Telegram. Listening...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"❌ Client Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Client stopped.")
