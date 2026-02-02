import asyncio
import logging
import sqlite3
import json
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import memory_manager
import roles
import routing_learner
import digest_manager
import memory_manager_v2 as mm2  # Advanced memory system

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
bot_instance = None # Global ref

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
                    # await bot_instance.send_message(uid, msg) # Optional: Don't spam unless requested
                except: pass
        
        # B. Weekly Digest (Sunday)
        if datetime.now().weekday() == 6: # Sunday
            weekly_d = await dm.generate_weekly_digest(uid)
            if weekly_d and bot_instance:
                 try: await bot_instance.send_message(uid, f"📅 **Weekly Report**\n\n{weekly_d.get('narrative')}")
                 except: pass

        # C. Monthly Digest (1st of Month)
        if datetime.now().day == 1:
            # Implementation omitted for brevity, similar flow
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
        
        await bot_instance.send_message(user_id, briefing)
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

async def proactive_checkin():
    """
    Optional: Schedule a morning greeting or focus reminder
    """
    pass

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
        
        # Schedule a quick "heartbeat" log every hour
        scheduler.add_job(
            lambda: logger.info("💓 System Heartbeat: Scheduler is alive"),
            CronTrigger(minute=0), # Every hour
            id="heartbeat",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("⏳ Scheduler started")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
