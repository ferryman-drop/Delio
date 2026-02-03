import logging
import sqlite3
import json
import uuid
import asyncio
from datetime import datetime, timedelta
import config
import memory_manager

logger = logging.getLogger(__name__)

class DigestManager:
    def __init__(self):
        self.mem_ctrl = memory_manager.global_memory

    async def generate_daily_digest(self, user_id: int):
        """Analyze last 24h of raw chat logs."""
        logger.info(f"🌞 Generating Daily Digest for {user_id}...")
        
        # 1. Fetch Raw Logs
        conn = sqlite3.connect('data/chat_history.db') # Legacy path, ideally move to memory_manager
        cursor = conn.cursor()
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT message, response, timestamp 
            FROM messages 
            WHERE user_id = ? AND timestamp > ? 
            ORDER BY timestamp ASC
        ''', (user_id, yesterday))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            logger.info("ℹ️ No messages to digest.")
            return None

        log_text = "\\n".join([f"[{r[2]}] User: {r[0]}\\nBot: {r[1]}" for r in rows[:100]]) # Limit context
        
        # 2. Summarize (Gemini)
        prompt = f"""
        ACT AS A PROFESSIONAL BIOGRAPHER.
        Summarize the user's day based on this chat log.
        
        LOG:
        {log_text}
        
        OUTPUT FORMAT (JSON):
        {{
            "narrative": "A paragraph describing key events and discussions.",
            "mood_score": 7, // 1-10
            "key_topics": ["topic1", "topic2"]
        }}
        """
        
        try:
            from google import genai
            client = genai.Client(api_key=config.GEMINI_KEY)
            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=config.MODEL_FAST,  # Flash Lite 2.0
                contents=prompt
            )
            data = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
            
            # 3. Save to Digests Table
            self._save_digest(user_id, 'daily', yesterday, datetime.now().strftime('%Y-%m-%d'), data['narrative'], data)
            logger.info("✅ Daily Digest Saved.")
            return data
        except Exception as e:
            logger.error(f"❌ Daily Digest Error: {e}")
            return None

    async def generate_weekly_digest(self, user_id: int):
        """Analyze last 7 Daily Digests."""
        logger.info(f"📅 Generating Weekly Digest for {user_id}...")
        
        # 1. Fetch last 7 Daily Digests
        digests = self._fetch_recent_digests(user_id, 'daily', 7)
        if not digests: return None
        
        combined_text = "\\n\\n".join([f"DAY {d['date']}: {d['content']}" for d in digests])
        
        # 2. Summarize
        prompt = f"""
        Analyze these 7 daily summaries.
        Write a WEEKLY REPORT.
        Focus on: Trends, Progress on Goals, Mood Shifts.
        
        INPUT:
        {combined_text}
        
        OUTPUT FORMAT (JSON):
        {{
            "narrative": "Weekly summary...",
            "mood_trend": "Increasing/Stable/Decreasing",
            "top_achievements": []
        }}
        """
        
        try:
            from google import genai
            client = genai.Client(api_key=config.GEMINI_KEY)
            resp = await asyncio.to_thread(
                client.models.generate_content,
                model=config.MODEL_FAST,
                contents=prompt
            )
            data = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
            
            self._save_digest(user_id, 'weekly', digests[-1]['date'], digests[0]['date'], data['narrative'], data)
            return data
        except Exception as e:
            logger.error(f"❌ Weekly Digest Error: {e}")
            return None

    def _save_digest(self, user_id, type_, start_date, end_date, content, metadata):
        conn = self.mem_ctrl.get_connection()
        try:
            conn.execute('''
                INSERT INTO digests (id, user_id, type, date_range, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), user_id, type_, f"{start_date}:{end_date}", content, json.dumps(metadata), datetime.now().isoformat()))
            conn.commit()
        finally:
            conn.close()

    def _fetch_recent_digests(self, user_id, type_, limit):
        conn = self.mem_ctrl.get_connection()
        try:
            rows = conn.execute('''
                SELECT content, timestamp, metadata FROM digests 
                WHERE user_id=? AND type=? 
                ORDER BY timestamp DESC LIMIT ?
            ''', (user_id, type_, limit)).fetchall()
            return [{"content": r[0], "date": r[1], "meta": json.loads(r[2])} for r in rows]
        finally:
            conn.close()

# Global Instance
digest_system = DigestManager()
