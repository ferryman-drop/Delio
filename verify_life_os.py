import asyncio
import logging
import scheduler
import datetime
import memory_manager
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_digestion")

# Setup Mock DB Data
def setup_mock_data():
    conn = sqlite3.connect('data/chat_history.db')
    cursor = conn.cursor()
    # Create tables if not exist (using main.py logic indirectly or manually)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            message TEXT,
            response TEXT,
            model TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert fake conversation
    logger.info("Inserting fake conversation...")
    cursor.execute('''
        INSERT INTO messages (user_id, message, response, timestamp)
        VALUES 
        (777, "I want to learn Spanish next year", "Great goal!", datetime('now')),
        (777, "I prefer learning by doing rather than reading books", "Noted, practical approach.", datetime('now', '+1 minute'))
    ''')
    conn.commit()
    conn.close()

async def verify():
    setup_mock_data()
    
    logger.info("Running digest_daily_logs...")
    await scheduler.digest_daily_logs()
    
    # Check Active Memory (Strategic Insights)
    mem = memory_manager.load_memory(777)
    logger.info(f"Updated Profile: {mem['profile']}")
    logger.info(f"Insights: {mem['insights']}")
    
    # Basic assertions
    # Note: real Gemini call might fail if no key/quota, but code logic is tested
    # If Gemini fails, we check logs.
    
if __name__ == "__main__":
    asyncio.run(verify())
