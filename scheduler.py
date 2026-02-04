import asyncio
import logging
import sqlite3
import json
import os
from datetime import datetime, timedelta
import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import memory_manager
import roles
import routing_learner
import digest_manager
import memory_manager_v2 as mm2  # Advanced memory system
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

    if await guard.try_enter_notify(user_id):
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
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT DISTINCT user_id FROM messages WHERE timestamp > ?", (yesterday,))
    users = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    if not users:
        logger.info("ℹ️ No active users today.")
        return

    dm = digest_manager.digest_system
    
    for uid in users:
        # A. Daily Digest (Always)
        daily_d = await dm.generate_daily_digest(uid)
        
        if daily_d:
            # Send Notification
            if bot_instance:
                try:
                    msg = f"🌙 **Daily Summary**\nmood: {daily_d.get('mood_score')}/10\n\n{daily_d.get('narrative')[:200]}..."
                    await safe_send_message(uid, msg, "DailyDigest")
                except: pass
        
        # B. Weekly Digest (Sunday)
        if datetime.now().weekday() == 6: # Sunday
            weekly_d = await dm.generate_weekly_digest(uid)
            if weekly_d:
                 await safe_send_message(uid, f"📅 **Weekly Report**\n\n{weekly_d.get('narrative')}", "WeeklyReport")
        if datetime.now().day == 1:
            pass

    logger.info("✅ Fractal Digestion complete")

async def send_morning_briefing(user_id, insights, goals):
    """
    Generate and send a morning briefing based on yesterday's analysis.
    """
    if not bot_instance:
        logger.warning("⚠️ Cannot send briefing: Bot instance not set")
        return

    try:
        import config
        from google import genai
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        insight_text = "\\n".join([f"- {i.get('description')}: {i.get('recommendation')}" for i in insights])
        goals_text = ", ".join(goals) if goals else "General Growth"
        
        prompt = f"""
        You are a Delio Assistant.
        The user has these new insights from yesterday:
        {insight_text}
        
        Focus Goals: {goals_text}
        
        Write a SHORT Morning Briefing (in Ukrainian).
        Structure:
        1. Greeting + "Focus of the Day"
        2. One key insight from yesterday and how to apply it today.
        3. A motivating closing.
        
        Keep it concise (under 500 chars).
        """
        
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_FAST,
            contents=prompt
        )
        briefing = response.text
        
        # Audio generation
        audio_path = None
        if len(briefing) > 250:
             from core.tts_service import tts
             audio_path = await tts.generate_speech(briefing)
        
        await safe_send_message(user_id, briefing, "MorningBriefing", audio_path)
        logger.info(f"📬 Sent Morning Briefing to {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send briefing to {user_id}: {e}")

async def proactive_checkin():
    pass

async def apply_memory_decay_all_users():
    """
    Apply TTL-based confidence decay to all users
    Runs daily at 3:00 AM
    """
    logger.info("🧹 Starting Memory Decay Cycle...")
    
    try:
        # Get all unique users from user_memory_v2
        conn = sqlite3.connect('data/bot_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT user_id FROM user_memory_v2")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not users:
            logger.info("ℹ️ No users with structured memory")
            return
        
        # Apply decay to each user
        if mm2.structured_memory:
            decay_engine = mm2.MemoryDecay(mm2.structured_memory)
            
            for user_id in users:
                try:
                    decay_engine.apply_decay(user_id)
                    logger.info(f"✅ Memory decay applied for user {user_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to apply decay for user {user_id}: {e}")
        
        logger.info(f"🧹 Memory Decay completed for {len(users)} users")
        
    except Exception as e:
        logger.error(f"❌ Memory Decay Cycle failed: {e}")

async def trigger_heartbeat():
    """
    Periodic heartbeat that enters the FSM for autonomous background tasks.
    Only triggers for active users who are currently IDLE.
    """
    logger.debug("💓 Triggering FSM Heartbeat")
    
    # 1. Get Active Users (Last 48h to be generous)
    try:
        conn = sqlite3.connect('data/chat_history.db')
        cursor = conn.cursor()
        since = (datetime.now() - timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT DISTINCT user_id FROM messages WHERE timestamp > ?", (since,))
        users = [r[0] for r in cursor.fetchall()]
        conn.close()
    except Exception as e:
        logger.error(f"❌ Failed to fetch users for heartbeat: {e}")
        users = []

    if not users:
        logger.debug("ℹ️ No active users for heartbeat.")
        return

    for user_id in users:
        # 2. Check State (Skip if busy)
        state = guard.get_state(user_id)
        if state != State.IDLE:
            logger.debug(f"⏳ Skipping heartbeat for {user_id} (State: {state.name})")
            continue
            
        # 3. Trigger FSM
        logger.info(f"💓 Heartbeat Check-in for user {user_id}")
        await fsm.process_event({
            "user_id": user_id,
            "type": "heartbeat",
            "text": "[SYSTEM_HEARTBEAT] Check context. If no critical action needed, reply 'SKIP'."
        })



def init_scheduler(bot=None):
    """Initialize and start the scheduler"""
    global bot_instance
    bot_instance = bot
    try:
        # Schedule Daily Digest at 4:00 AM
        scheduler.add_job(
            digest_daily_logs,
            CronTrigger(hour=4, minute=0),
            id="daily_digest",
            replace_existing=True
        )

        # Schedule Routing Learning Cycle (05:00)
        scheduler.add_job(
            routing_learner.run_learning_cycle,
            CronTrigger(hour=5, minute=0),
            id="routing_learning",
            replace_existing=True
        )
        
        # Schedule Memory Decay (03:00 AM - before daily digest)
        scheduler.add_job(
            apply_memory_decay_all_users,
            CronTrigger(hour=3, minute=0),
            id="memory_decay",
            replace_existing=True
        )
        
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
