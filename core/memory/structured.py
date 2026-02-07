"""
Structured Memory Manager (Async)
Based on legacy/memory_manager_v2.py but ported to aiosqlite for Delio Core.

Sections:
1. core_identity - Who you are
2. life_level - Current level & trajectory
3. time_energy - Time allocation & focus
4. skills_map - Hard/soft skills
5. money_model - Income & financial state
6. goals - Primary goals & direction
7. decision_patterns - How you decide
8. behavior_discipline - Execution consistency
9. trust_communication - Trust level & preferred mode
10. feedback_signals - What works/doesn't work
"""

import aiosqlite
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import os
import uuid

logger = logging.getLogger("Delio.Memory.Structured")

# TTL Categories (days)
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

DEFAULT_CONFIDENCE = 0.5

class StructuredMemory:
    """Manages structured 9-section user memory with confidence scoring (Async)"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._ensure_dir()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def _get_conn(self):
        """Get or create persistent connection."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def init_db(self):
        """Initialize database tables"""
        db = await self._get_conn()

        await db.execute('''
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

        await db.execute('''
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
        await db.commit()
        logger.info(f"✅ Structured Memory initialized at {self.db_path}")

    async def get_memory(self, user_id: int, section: str, key: str) -> Optional[Dict[str, Any]]:
        """Get memory item with confidence score"""
        db = await self._get_conn()
        async with db.execute('''
            SELECT value, confidence, last_confirmed, ttl_days, created_at, updated_at
            FROM user_memory_v2
            WHERE user_id = ? AND section = ? AND key = ?
        ''', (user_id, section, key)) as cursor:
            row = await cursor.fetchone()

            if not row:
                return None

            try:
                value_data = json.loads(row['value'])
            except:
                value_data = row['value']

            return {
                'value': value_data,
                'confidence': row['confidence'],
                'last_confirmed': row['last_confirmed'],
                'ttl_days': row['ttl_days'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }

    async def set_memory(self, user_id: int, section: str, key: str, value: Any,
                   confidence: float = DEFAULT_CONFIDENCE, metadata: Optional[Dict] = None):
        """Set or update memory item"""
        now = datetime.now().isoformat()
        ttl_days = TTL_MAP.get(section, 90)

        # Serialize value
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = json.dumps({"value": value})

        db = await self._get_conn()
        # Upsert logic
        await db.execute('''
            INSERT INTO user_memory_v2
            (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, section, key) DO UPDATE SET
                value=excluded.value,
                confidence=excluded.confidence,
                last_confirmed=excluded.last_confirmed,
                updated_at=excluded.updated_at,
                metadata=excluded.metadata
        ''', (
            user_id, section, key, value_str, confidence, now, ttl_days, now, now,
            json.dumps(metadata) if metadata else None
        ))
        await db.commit()
        logger.debug(f"💾 Memory set: {section}.{key} (Conf: {confidence})")

    async def get_all_memory(self, user_id: int, min_confidence: float = 0.0) -> Dict[str, Dict]:
        """Get all memory sections for a user"""
        db = await self._get_conn()
        async with db.execute('''
            SELECT section, key, value, confidence, last_confirmed
            FROM user_memory_v2
            WHERE user_id = ? AND confidence >= ?
            ORDER BY section, confidence DESC
        ''', (user_id, min_confidence)) as cursor:
            rows = await cursor.fetchall()

            result = {}
            for row in rows:
                section = row['section']
                if section not in result: result[section] = {}

                try: val = json.loads(row['value'])
                except: val = row['value']

                result[section][row['key']] = {
                    'value': val,
                    'confidence': row['confidence']
                }
            return result

    async def create_snapshot(self, user_id: int) -> str:
        """Create a full snapshot of user memory"""
        mem_data = await self.get_all_memory(user_id)
        if not mem_data: return None

        snapshot_id = str(uuid.uuid4())
        now = datetime.now()
        snapshot_date = now.isoformat()
        quarter = f"Q{(now.month-1)//3 + 1}-{now.year}"

        # Extract Life Level if present
        life_level = "Unknown"
        conf = 0.0
        if 'life_level' in mem_data:
             # Logic to extract value depending on structure
             pass

        db = await self._get_conn()
        await db.execute('''
            INSERT INTO memory_snapshots
            (id, user_id, snapshot_date, quarter, life_level, life_level_confidence, summary, full_snapshot, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot_id, user_id, snapshot_date, quarter, life_level, conf,
            f"Manual Snapshot {snapshot_date}", json.dumps(mem_data), snapshot_date
        ))
        await db.commit()
        return snapshot_id

    async def close(self):
        """Close persistent connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
