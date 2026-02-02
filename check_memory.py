#!/usr/bin/env python3
"""
Check Memory V2 - View structured memory contents
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "/root/ai_assistant/data/bot_data.db"

def check_memory():
    """Check user_memory_v2 contents"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_memory_v2'")
    if not cursor.fetchone():
        print("❌ user_memory_v2 table not found")
        return
    
    # Get all memory entries
    cursor.execute("""
        SELECT user_id, section, key, value, confidence, last_confirmed, created_at
        FROM user_memory_v2
        ORDER BY user_id, section, confidence DESC
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("📭 No memory entries yet (waiting for first interaction)")
        print("\n💡 Test by sending a message to the bot:")
        print("   'Хочу створити AI-асистента'")
        return
    
    print(f"🧠 Memory Entries: {len(rows)}\n")
    
    current_user = None
    current_section = None
    
    for row in rows:
        user_id, section, key, value, confidence, last_confirmed, created_at = row
        
        if user_id != current_user:
            current_user = user_id
            print(f"\n👤 User ID: {user_id}")
            print("=" * 60)
        
        if section != current_section:
            current_section = section
            print(f"\n📂 {section.upper()}")
        
        # Parse value
        try:
            value_data = json.loads(value)
            if isinstance(value_data, dict) and 'value' in value_data:
                display_value = value_data['value']
            else:
                display_value = value_data
        except:
            display_value = value
        
        # Format display
        print(f"  • {key}: {display_value}")
        print(f"    Confidence: {confidence:.2f} | Last confirmed: {last_confirmed[:10]}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ Total entries: {len(rows)}")

def check_tables():
    """Check all new tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables = ['user_memory_v2', 'memory_conflicts', 'memory_snapshots', 'anomaly_events']
    
    print("📊 Table Status:\n")
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        status = "✅" if count > 0 else "📭"
        print(f"{status} {table}: {count} entries")
    
    conn.close()

if __name__ == "__main__":
    print("🔍 Checking Advanced Memory System...\n")
    check_tables()
    print("\n" + "=" * 60 + "\n")
    check_memory()
