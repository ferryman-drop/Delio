import asyncio
import logging
import sys
import os

# Ensure legacy path is available for imports
_legacy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../legacy'))
if _legacy_path not in sys.path:
    sys.path.insert(0, _legacy_path)

from core.fsm import instance as fsm
from core.state import State
from core.context import ExecutionContext
import config

# Import States
from states.observe import ObserveState
from states.retrieve import RetrieveState
from states.plan import PlanState
from states.decide import DecideState
from states.act import ActState
from states.respond import RespondState
from states.reflect import ReflectState
from states.memory_write import MemoryWriteState
from states.error import ErrorState
from states.deep_think import DeepThinkState

# Import Subsystems
import core.logger
import core.tools
import scheduler
from core.state_guard import guard
import memory_manager_v2 as mm2
import memory_populator
import model_control

logger = logging.getLogger("Delio.Engine")

class HeadlessBot:
    """Mock Bot for Headless execution with real Telegram fallback."""
    def __init__(self, real_bot=None):
        self._real_bot = real_bot
        self.session = self._Session()
        
    class _Session:
        async def close(self): pass

    async def send_message(self, chat_id, text, parse_mode=None):
        logger.info(f"🤖 [HEADLESS BOT] Output to {chat_id}: {text[:50]}...")
        if self._real_bot:
            try:
                await self._real_bot.send_message(chat_id, text, parse_mode=parse_mode)
            except Exception as e:
                logger.error(f"Failed to send real message from HeadlessBot: {e}")

    async def edit_message_text(self, text, chat_id, message_id, parse_mode=None):
        logger.info(f"🤖 [HEADLESS BOT] Editing message {message_id} for {chat_id}")
        if self._real_bot:
            try:
                await self._real_bot.edit_message_text(text, chat_id, message_id, parse_mode=parse_mode)
            except Exception as e:
                logger.error(f"Failed to edit real message from HeadlessBot: {e}")

    async def set_my_commands(self, commands):
        if self._real_bot:
            await self._real_bot.set_my_commands(commands)

_engine_initialized = False

def init_engine(real_bot=None):
    global _engine_initialized
    if _engine_initialized:
        return

    # 1. Logging
    core.logger.setup_logging("logs/delio_api.json", level=config.LOG_LEVEL)
    
    # 2. Init Bot
    bot = HeadlessBot(real_bot=real_bot)
    
    # 3. Register States
    fsm.register_handler(State.OBSERVE, ObserveState())
    fsm.register_handler(State.RETRIEVE, RetrieveState())
    fsm.register_handler(State.PLAN, PlanState())
    fsm.register_handler(State.DECIDE, DecideState())
    fsm.register_handler(State.ACT, ActState())
    fsm.register_handler(State.RESPOND, RespondState(bot))
    fsm.register_handler(State.REFLECT, ReflectState(bot))
    fsm.register_handler(State.MEMORY_WRITE, MemoryWriteState())
    fsm.register_handler(State.DEEP_THINK, DeepThinkState(bot))
    fsm.register_handler(State.ERROR, ErrorState(bot))
    
    # 4. Memory V2
    db_path = config.SQLITE_DB_PATH
    structured_memory = mm2.init_structured_memory(db_path)
    memory_populator.init_memory_populator(structured_memory)
    model_control.init_model_controller(structured_memory)
    
    # 5. Guard & Scheduler
    guard.set_bot(bot)
    scheduler.init_scheduler(bot)
    
    logger.info("✅ Delio Headless Engine Initialized")
    _engine_initialized = True

async def process_request(user_id: int, text: str, message_id: int = None, platform: str = "api") -> ExecutionContext:
    """
    Process a request through the FSM and return the final ExecutionContext.
    """
    if not _engine_initialized:
        init_engine()
        
    logger.info(f"🚀 Processing API Request for {user_id}: {text[:20]}...")
    
    # 1. Intent Classification (Phase 2)
    from core.router import router
    intent = await router.classify(text)
    logger.info(f"🚦 Intent Classified: {intent}")

    event_data = {
        "user_id": user_id,
        "type": "message",
        "text": text,
        "intent": intent, # Pass to context
        "metadata": {"platform": platform, "message_id": message_id}
    }
    
    # Run FSM
    context = await fsm.process_event(event_data)
    
    return context
