#!/usr/bin/env python3
"""
Migration Script: user_profiles → user_memory_v2
Big Bang Migration for Delio Advanced Memory Architecture

CRITICAL: This script will:
1. Backup existing database
2. Create new user_memory_v2 table
3. Migrate all existing data
4. Validate migration
5. Archive old tables (not delete)

Author: Antigravity
Date: 2026-02-01
"""

import sqlite3
import json
import shutil
from datetime import datetime
from pathlib import Path

# Paths
DB_PATH = "/root/ai_assistant/data/bot_data.db"
BACKUP_PATH = f"/root/ai_assistant/data/bot_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

# Default confidence scores
DEFAULT_CONFIDENCE = 0.5
HIGH_CONFIDENCE = 0.7  # for explicitly set data

# TTL categories (days)
TTL_MAP = {
    "core_identity": 365,
    "life_level": 90,
    "time_energy": 14,
    "skills_map": 120,
    "money_model": 90,
    "goals": 60,
    "decision_patterns": 45,
    "behavior_discipline": 45,
    "trust_communication": 120,
    "feedback_signals": 30
}

def backup_database():
    """Create backup before migration"""
    print(f"📦 Creating backup: {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"✅ Backup created successfully")

def create_new_schema(conn):
    """Create user_memory_v2 table"""
    print("🏗️  Creating user_memory_v2 schema...")
    
    cursor = conn.cursor()
    
    # Main memory table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_memory_v2 (
            user_id INTEGER,
            section TEXT,
            key TEXT,
            value TEXT,
            confidence REAL DEFAULT 0.5,
            last_confirmed TEXT,
            ttl_days INTEGER,
            created_at TEXT,
            updated_at TEXT,
            metadata TEXT,
            PRIMARY KEY (user_id, section, key)
        )
    ''')
    
    # Conflict states table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_conflicts (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            section TEXT,
            key TEXT,
            old_value TEXT,
            new_value TEXT,
            old_confidence REAL,
            new_confidence REAL,
            status TEXT DEFAULT 'unresolved',
            detected_at TEXT,
            resolved_at TEXT
        )
    ''')
    
    # Quarterly snapshots table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_snapshots (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            snapshot_date TEXT,
            quarter TEXT,
            life_level TEXT,
            life_level_confidence REAL,
            summary TEXT,
            full_snapshot TEXT,
            created_at TEXT
        )
    ''')
    
    # Anomaly events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS anomaly_events (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            type TEXT,
            signal TEXT,
            severity TEXT,
            confidence REAL,
            detected_at TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    conn.commit()
    print("✅ New schema created")

def migrate_user_profiles(conn):
    """Migrate existing user_profiles to user_memory_v2"""
    print("🔄 Migrating user_profiles...")
    
    cursor = conn.cursor()
    
    # Fetch existing profiles
    cursor.execute("SELECT user_id, core_values, long_term_goals, decision_patterns FROM user_profiles")
    profiles = cursor.fetchall()
    
    if not profiles:
        print("⚠️  No profiles found to migrate")
        return
    
    now = datetime.now().isoformat()
    
    for user_id, core_values, goals, patterns in profiles:
        print(f"  Migrating user {user_id}...")
        
        # Parse JSON (if stored as JSON)
        try:
            values = json.loads(core_values) if core_values else []
            goals_list = json.loads(goals) if goals else []
            patterns_list = json.loads(patterns) if patterns else []
        except:
            values = [core_values] if core_values else []
            goals_list = [goals] if goals else []
            patterns_list = [patterns] if patterns else []
        
        # Migrate to core_identity section
        if values:
            cursor.execute('''
                INSERT OR REPLACE INTO user_memory_v2 
                (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                'core_identity',
                'core_values',
                json.dumps({"value": values, "confidence": HIGH_CONFIDENCE}),
                HIGH_CONFIDENCE,
                now,
                TTL_MAP['core_identity'],
                now,
                now
            ))
        
        # Migrate to goals section
        if goals_list:
            cursor.execute('''
                INSERT OR REPLACE INTO user_memory_v2 
                (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                'goals',
                'primary_goals',
                json.dumps({"value": goals_list, "confidence": HIGH_CONFIDENCE}),
                HIGH_CONFIDENCE,
                now,
                TTL_MAP['goals'],
                now,
                now
            ))
        
        # Migrate to decision_patterns section
        if patterns_list:
            cursor.execute('''
                INSERT OR REPLACE INTO user_memory_v2 
                (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                'decision_patterns',
                'patterns',
                json.dumps({"value": patterns_list, "confidence": DEFAULT_CONFIDENCE}),
                DEFAULT_CONFIDENCE,
                now,
                TTL_MAP['decision_patterns'],
                now,
                now
            ))
    
    conn.commit()
    print(f"✅ Migrated {len(profiles)} user profiles")

def migrate_routing_events(conn):
    """Extract Life Level from routing_events"""
    print("🔄 Extracting Life Level from routing_events...")
    
    cursor = conn.cursor()
    
    # Get most recent life_level for each user
    cursor.execute('''
        SELECT user_id, life_level, COUNT(*) as count
        FROM routing_events
        WHERE life_level IS NOT NULL
        GROUP BY user_id, life_level
        ORDER BY count DESC
    ''')
    
    life_levels = cursor.fetchall()
    now = datetime.now().isoformat()
    
    for user_id, life_level, count in life_levels:
        # Calculate confidence based on consistency
        confidence = min(0.9, 0.5 + (count / 100) * 0.4)
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_memory_v2 
            (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            'life_level',
            'current_level',
            json.dumps({"value": life_level, "confidence": confidence}),
            confidence,
            now,
            TTL_MAP['life_level'],
            now,
            now
        ))
    
    conn.commit()
    print(f"✅ Extracted Life Level for {len(life_levels)} users")

def initialize_empty_sections(conn):
    """Initialize empty sections for all users with default values"""
    print("🔄 Initializing empty sections...")
    
    cursor = conn.cursor()
    
    # Get all unique users
    cursor.execute("SELECT DISTINCT user_id FROM user_memory_v2")
    users = [row[0] for row in cursor.fetchall()]
    
    now = datetime.now().isoformat()
    
    for user_id in users:
        # Check which sections are missing
        cursor.execute("SELECT DISTINCT section FROM user_memory_v2 WHERE user_id = ?", (user_id,))
        existing_sections = {row[0] for row in cursor.fetchall()}
        
        # Initialize missing sections with placeholder
        for section in TTL_MAP.keys():
            if section not in existing_sections:
                cursor.execute('''
                    INSERT INTO user_memory_v2 
                    (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    section,
                    '_initialized',
                    json.dumps({"value": None, "confidence": 0.1}),
                    0.1,
                    now,
                    TTL_MAP[section],
                    now,
                    now
                ))
    
    conn.commit()
    print(f"✅ Initialized empty sections for {len(users)} users")

def validate_migration(conn):
    """Validate migration success"""
    print("🔍 Validating migration...")
    
    cursor = conn.cursor()
    
    # Check if new tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_memory_v2'")
    if not cursor.fetchone():
        raise Exception("❌ Migration failed: user_memory_v2 table not created!")
    
    # Check user_memory_v2 data
    cursor.execute("SELECT COUNT(*) FROM user_memory_v2")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("⚠️  No existing data to migrate (empty database)")
        print("✅ Structure created - will auto-populate on first interactions")
    else:
        print(f"✅ Validation passed: {count} memory entries migrated")
        
        # Show summary
        cursor.execute("SELECT section, COUNT(*) FROM user_memory_v2 GROUP BY section")
        sections = cursor.fetchall()
        
        print("\n📊 Memory sections:")
        for section, cnt in sections:
            print(f"  {section}: {cnt} entries")

def archive_old_tables(conn):
    """Rename old tables (don't delete)"""
    print("📦 Archiving old tables...")
    
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    cursor.execute(f"ALTER TABLE user_profiles RENAME TO user_profiles_archived_{timestamp}")
    
    conn.commit()
    print("✅ Old tables archived")

def main():
    """Main migration flow"""
    print("=" * 60)
    print("🚀 Delio Advanced Memory Migration")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Backup
        backup_database()
        print()
        
        # Step 2: Connect to DB
        print("🔌 Connecting to database...")
        conn = sqlite3.connect(DB_PATH)
        print("✅ Connected")
        print()
        
        # Step 3: Create new schema
        create_new_schema(conn)
        print()
        
        # Step 4: Migrate data
        migrate_user_profiles(conn)
        print()
        
        migrate_routing_events(conn)
        print()
        
        initialize_empty_sections(conn)
        print()
        
        # Step 5: Validate
        validate_migration(conn)
        print()
        
        # Step 6: Archive old tables
        archive_old_tables(conn)
        print()
        
        conn.close()
        
        print("=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print(f"\n📦 Backup saved at: {BACKUP_PATH}")
        print("🔄 Old tables archived (not deleted)")
        print("\n🚀 You can now restart the bot with new memory system!")
        
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        print(f"📦 Database backup is safe at: {BACKUP_PATH}")
        print("🔄 You can restore from backup if needed")
        raise

if __name__ == "__main__":
    main()
