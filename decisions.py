
import os
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "data", "bot_data.db")

def init_decisions_db():
    """Initialize decisions table in database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp DATETIME,
                topic TEXT,
                context TEXT,
                result TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Decisions table initialized")
    except Exception as e:
        logger.error(f"❌ Error initializing decisions DB: {e}")

def add_decision(user_id: int, topic: str, context: str, result: str):
    """Save a strategic decision to the DB"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO decisions (user_id, timestamp, topic, context, result)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, timestamp, topic, context, result))
        
        conn.commit()
        conn.close()
        logger.info(f"📌 Recorded strategic decision for user {user_id}: {topic}")
        return True
    except Exception as e:
        logger.error(f"❌ Error saving decision: {e}")
        return False

def get_recent_decisions(user_id: int, limit: int = 5):
    """Retrieve recent decisions for a user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT topic, context, result, timestamp FROM decisions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"❌ Error reading decisions: {e}")
        return []
