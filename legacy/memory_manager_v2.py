"""
Memory Manager V2 - Advanced Memory Architecture
Implements structured 9-section memory with confidence scoring and auto-population

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

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid

logger = logging.getLogger(__name__)

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

# Default confidence scores
DEFAULT_CONFIDENCE = 0.5
HIGH_CONFIDENCE = 0.7
LOW_CONFIDENCE = 0.3

class StructuredMemory:
    """Manages structured 9-section user memory with confidence scoring"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_memory(self, user_id: int, section: str, key: str) -> Optional[Dict[str, Any]]:
        """Get memory item with confidence score"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT value, confidence, last_confirmed, ttl_days, created_at, updated_at
            FROM user_memory_v2
            WHERE user_id = ? AND section = ? AND key = ?
        ''', (user_id, section, key))
        
        row = cursor.fetchone()
        conn.close()
        
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
    
    def set_memory(self, user_id: int, section: str, key: str, value: Any, 
                   confidence: float = DEFAULT_CONFIDENCE, metadata: Optional[Dict] = None):
        """Set or update memory item"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        ttl_days = TTL_MAP.get(section, 90)
        
        # Serialize value
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = json.dumps({"value": value})
        
        # Check if exists
        existing = self.get_memory(user_id, section, key)
        
        if existing:
            # Update existing
            cursor.execute('''
                UPDATE user_memory_v2
                SET value = ?, confidence = ?, last_confirmed = ?, updated_at = ?, metadata = ?
                WHERE user_id = ? AND section = ? AND key = ?
            ''', (
                value_str,
                confidence,
                now,
                now,
                json.dumps(metadata) if metadata else None,
                user_id,
                section,
                key
            ))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO user_memory_v2
                (user_id, section, key, value, confidence, last_confirmed, ttl_days, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                section,
                key,
                value_str,
                confidence,
                now,
                ttl_days,
                now,
                now,
                json.dumps(metadata) if metadata else None
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💾 Memory set: user={user_id}, section={section}, key={key}, confidence={confidence:.2f}")
    
    def get_section(self, user_id: int, section: str) -> Dict[str, Any]:
        """Get all memory items in a section"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT key, value, confidence, last_confirmed
            FROM user_memory_v2
            WHERE user_id = ? AND section = ?
        ''', (user_id, section))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {}
        for row in rows:
            try:
                value_data = json.loads(row['value'])
            except:
                value_data = row['value']
            
            result[row['key']] = {
                'value': value_data,
                'confidence': row['confidence'],
                'last_confirmed': row['last_confirmed']
            }
        
        return result
    
    def get_all_memory(self, user_id: int, min_confidence: float = 0.0) -> Dict[str, Dict]:
        """Get all memory sections for a user (filtered by confidence)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT section, key, value, confidence, last_confirmed
            FROM user_memory_v2
            WHERE user_id = ? AND confidence >= ?
            ORDER BY section, confidence DESC
        ''', (user_id, min_confidence))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {}
        for row in rows:
            section = row['section']
            if section not in result:
                result[section] = {}
            
            try:
                value_data = json.loads(row['value'])
            except:
                value_data = row['value']
            
            result[section][row['key']] = {
                'value': value_data,
                'confidence': row['confidence'],
                'last_confirmed': row['last_confirmed']
            }
        
        return result
    
    def update_confidence(self, user_id: int, section: str, key: str, delta: float):
        """Update confidence score (incremental)"""
        existing = self.get_memory(user_id, section, key)
        
        if not existing:
            logger.warning(f"Cannot update confidence: memory not found")
            return
        
        new_confidence = max(0.1, min(0.95, existing['confidence'] + delta))
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE user_memory_v2
            SET confidence = ?, last_confirmed = ?, updated_at = ?
            WHERE user_id = ? AND section = ? AND key = ?
        ''', (new_confidence, now, now, user_id, section, key))
        
        conn.commit()
        conn.close()
        
        conn.commit()
        conn.close()
        
        logger.info(f"📈 Confidence updated: {section}.{key}: {existing['confidence']:.2f} → {new_confidence:.2f}")

    def create_snapshot(self, user_id: int) -> str:
        """Create a full snapshot of user memory"""
        # 1. Get all current memory
        mem_data = self.get_all_memory(user_id)
        if not mem_data:
            return None
            
        # 2. Prepare Meta
        snapshot_id = str(uuid.uuid4())
        now = datetime.now()
        snapshot_date = now.isoformat()
        quarter = f"Q{(now.month-1)//3 + 1}-{now.year}"
        
        # Get Life Level
        life_level = "Unknown"
        ll_conf = 0.0
        if 'life_level' in mem_data and 'current_level' in mem_data['life_level']:
            val = mem_data['life_level']['current_level']
            life_level = val['value'] if isinstance(val, dict) else val
            ll_conf = mem_data['life_level']['current_level']['confidence']

        # 3. Save to DB
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO memory_snapshots
                (id, user_id, snapshot_date, quarter, life_level, life_level_confidence, summary, full_snapshot, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_id,
                user_id,
                snapshot_date,
                quarter,
                life_level,
                ll_conf,
                f"Manual Snapshot {snapshot_date}",
                json.dumps(mem_data),
                snapshot_date
            ))
            conn.commit()
            logger.info(f"📸 Snapshot created: {snapshot_id} for user {user_id}")
            return snapshot_id
        except Exception as e:
            logger.error(f"❌ Snapshot failed: {e}")
            return None
        finally:
            conn.close()


class ConfidenceEngine:
    """Manages confidence scoring logic"""
    
    def __init__(self, memory: StructuredMemory):
        self.memory = memory
    
    def confirm_signal(self, user_id: int, section: str, key: str, value: Any):
        """Confirm a signal - increase confidence if value matches"""
        existing = self.memory.get_memory(user_id, section, key)
        
        if not existing:
            # New signal - set with default confidence
            self.memory.set_memory(user_id, section, key, value, DEFAULT_CONFIDENCE)
            return
        
        # Check if value matches
        existing_value = existing['value'].get('value') if isinstance(existing['value'], dict) else existing['value']
        
        if existing_value == value:
            # Same value - increase confidence
            self.memory.update_confidence(user_id, section, key, +0.1)
        else:
            # Different value - create conflict
            self._create_conflict(user_id, section, key, existing_value, value, existing['confidence'])
    
    def _create_conflict(self, user_id: int, section: str, key: str, 
                        old_value: Any, new_value: Any, old_confidence: float):
        """Create conflict record for resolution"""
        conn = self.memory.get_connection()
        cursor = conn.cursor()
        
        conflict_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO memory_conflicts
            (id, user_id, section, key, old_value, new_value, old_confidence, new_confidence, status, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conflict_id,
            user_id,
            section,
            key,
            json.dumps(old_value),
            json.dumps(new_value),
            old_confidence,
            DEFAULT_CONFIDENCE,
            'unresolved',
            now
        ))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"⚠️ Conflict detected: {section}.{key}: {old_value} vs {new_value}")


class MemoryDecay:
    """Handles TTL-based confidence decay"""
    
    def __init__(self, memory: StructuredMemory):
        self.memory = memory
    
    def apply_decay(self, user_id: int):
        """Apply decay to all memory items based on TTL"""
        conn = self.memory.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT section, key, confidence, last_confirmed, ttl_days
            FROM user_memory_v2
            WHERE user_id = ?
        ''', (user_id,))
        
        rows = cursor.fetchall()
        now = datetime.now()
        
        for row in rows:
            last_confirmed = datetime.fromisoformat(row['last_confirmed'])
            days_passed = (now - last_confirmed).days
            ttl_days = row['ttl_days']
            
            if days_passed > ttl_days:
                # Calculate decay
                decay_factor = min(0.3, (days_passed / ttl_days) * 0.1)
                new_confidence = max(0.1, row['confidence'] - decay_factor)
                
                cursor.execute('''
                    UPDATE user_memory_v2
                    SET confidence = ?, updated_at = ?
                    WHERE user_id = ? AND section = ? AND key = ?
                ''', (new_confidence, now.isoformat(), user_id, row['section'], row['key']))
                
                logger.info(f"📉 Decay applied: {row['section']}.{row['key']}: {row['confidence']:.2f} → {new_confidence:.2f}")
        
        conn.commit()
        conn.close()


# Global instance (will be initialized in main.py)
structured_memory = None

def init_structured_memory(db_path: str):
    """Initialize global structured memory instance"""
    global structured_memory
    structured_memory = StructuredMemory(db_path)
    logger.info("✅ Structured Memory V2 initialized")
    return structured_memory
