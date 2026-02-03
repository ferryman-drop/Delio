
import sqlite3
import os

DB_PATH = "/root/ai_assistant/data/chat_history.db"

def inspect_db():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- LAST 10 MESSAGES ---")
    cursor.execute("SELECT id, user_id, message, response, model FROM messages ORDER BY id DESC LIMIT 10;")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | User: {row[1]} | Model: {row[4]}")
        print(f"Q: {row[2][:200]}")
        print(f"A: {row[3][:300]}")
        print("-" * 20)
        
    conn.close()

if __name__ == "__main__":
    inspect_db()
