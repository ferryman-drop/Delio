import asyncio
import logging
import sqlite3
import json
import os
from datetime import datetime, timedelta
import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
# import memory_manager
# import roles
# import routing_learner
# import digest_manager
# import memory_manager_v2 as mm2  # Advanced memory system
from core.fsm import instance as fsm
from core.state import State
from core.state_guard import guard

logger = logging.getLogger(__name__)

# TODO: Switch to SQLite JobStore for persistence:
# scheduler = AsyncIOScheduler(jobstores={'default': SQLAlchemyJobStore(url='sqlite:///data/jobs.sqlite')})
scheduler = AsyncIOScheduler()
bot_instance = None # Global ref

async def safe_send_message(user_id: int, text: str, model_tag: str = "System", audio_path: str = None):
    """
    Safely send a message through the StateGuard.
    If user is busy, reschedule or drop (depending on importance).
    """
    if not bot_instance:
        logger.warning(f"⚠️ Cannot send message to {user_id}: Bot instance not set")
        return False

    if guard.try_enter_notify(user_id):
        try:
            if audio_path:
                 from aiogram.types import FSInputFile
                 voice = FSInputFile(audio_path)
                 await bot_instance.send_voice(user_id, voice, caption=text[:1000])
                 logger.info(f"🎙️ Safe voice sent to {user_id}")
            else:
                 await bot_instance.send_message(user_id, text)
                 logger.info(f"📨 Safe message sent to {user_id}")
            
            # Record in memory
            try:
                import old_memory as memory
                memory.save_interaction(user_id, f"[SYSTEM_EVENT: {model_tag}]", text, model_tag)
            except: pass
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send safe message: {e}")
            return False
        finally:
            guard.force_idle(user_id)
    else:
        logger.info(f"⏳ User {user_id} busy. Message queued/delayed.")
        return False

async def digest_daily_logs():
    """
    Fractal Memory: Daily -> Weekly -> Monthly Cycles.
    """
    logger.info("🌙 Starting Fractal Digestion...")
    
    # 1. Identify Active Users (Last 24h)
    # Ideally, maintain a 'users' table. For now, scan recent messages.
    db_path = os.path.join(os.path.dirname(__file__), 'data/bot_data.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT DISTINCT user_id FROM routing_events WHERE timestamp > ?", (yesterday,))
    users = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    if not users:
        logger.info("ℹ️ No active users today.")
        return

    # dm = digest_manager.digest_system
    # 
    # for uid in users:
    #     # A. Daily Digest (Always)
    #     pass

async def send_morning_briefing(user_id, insights, goals):
    pass

async def proactive_checkin():
    pass

async def apply_memory_decay_all_users():
    """
    Apply TTL-based confidence decay to all users
    Runs daily at 3:00 AM
    """
    logger.info("🧹 Starting Memory Decay Cycle...")
    # disabled due to missing modules
    pass

async def trigger_heartbeat():
    """
    Periodic heartbeat that enters the FSM for autonomous background tasks.
    Only triggers for active users who are currently IDLE.
    """
    # 1. Get Active Users (Last 48h)
    users = []
    try:
        # Use bot_data.db from config if possible
        db_path = "/root/ai_assistant/data/bot_data.db"
        
        # Connect
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query routing_events for user activity
        since = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
        sql = "SELECT DISTINCT user_id FROM routing_events WHERE timestamp > ?"
        cursor.execute(sql, (since,))
        
        users = [r[0] for r in cursor.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"❌ Failed to fetch users for heartbeat: {e}")
        return

    if not users:
        return

    logger.debug(f"💓 Heartbeat candidates: {len(users)}")

    for user_id in users:
        # 2. Check State (Skip if busy)
        state = guard.get_state(user_id)
        if state != State.IDLE:
            continue
            
        # 3. Trigger FSM via Background Task
        # We launch it as a background task so heartbeat job doesn't block
        asyncio.create_task(fsm.process_event({
            "user_id": user_id,
            "type": "heartbeat",
            "text": "SYSTEM_HEARTBEAT"
        }))



def init_scheduler(bot=None):
    """Initialize and start the scheduler"""
    global bot_instance
    bot_instance = bot
    try:
        # Schedule Daily Digest at 4:00 AM
        # scheduler.add_job(
        #     digest_daily_logs,
        #     CronTrigger(hour=4, minute=0),
        #     id="daily_digest",
        #     replace_existing=True
        # )

        # Schedule Routing Learning Cycle (05:00)
        # scheduler.add_job(
        #     routing_learner.run_learning_cycle,
        #     CronTrigger(hour=5, minute=0),
        #     id="routing_learning",
        #     replace_existing=True
        # )
        
        # Schedule Memory Decay (03:00 AM - before daily digest)
        # scheduler.add_job(
        #     apply_memory_decay_all_users,
        #     CronTrigger(hour=3, minute=0),
        #     id="memory_decay",
        #     replace_existing=True
        # )
        
        # Schedule a real FSM heartbeat using config
        scheduler.add_job(
            trigger_heartbeat,
            CronTrigger(minute=f"*/{config.HEARTBEAT_INTERVAL_MINUTES}"),
            id="fsm_heartbeat",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("⏳ Scheduler started")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
