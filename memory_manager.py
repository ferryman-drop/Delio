import os
import json
import logging
import sqlite3
import asyncio
from datetime import datetime
import uuid
from typing import List, Dict, Any, Optional

import memory  # ChromaDB / Vector Search wrapper
import prefs   # User preferences

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "data", "bot_data.db")
CHAT_HISTORY_DB_PATH = os.path.join(os.getcwd(), "data", "chat_history.db")

class MemoryController:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    def init_db(self):
        """Initialize Strategic Memory Database with Optimization"""
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            cursor = conn.cursor()
            
            # Profile table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INTEGER PRIMARY KEY,
                    core_values TEXT,
                    long_term_goals TEXT,
                    decision_patterns TEXT
                )
            ''')
            
            # Decisions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategic_decisions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    date TEXT,
                    topic TEXT,
                    context TEXT,
                    rationale TEXT,
                    expected_outcome TEXT,
                    status TEXT,
                    tags TEXT,
                    review_date TEXT
                )
            ''')
            
            # Insights table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategic_insights (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    date TEXT,
                    type TEXT,
                    description TEXT,
                    evidence TEXT,
                    recommendation TEXT
                )
            ''')

            # Audit Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    date TEXT,
                    query TEXT,
                    response TEXT,
                    efficiency_score INTEGER,
                    critique TEXT,
                    model_used TEXT
                )
            ''')

            # User Notes (Persistence Layer)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_notes (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    topic TEXT,
                    content TEXT,
                    created_at TEXT
                )
            ''')
            
            # Digest Ledger (Fractal Memory)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS digests (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    type TEXT, -- daily, weekly, monthly
                    date_range TEXT, -- YYYY-MM-DD:YYYY-MM-DD
                    content TEXT,
                    metadata TEXT, -- JSON
                    timestamp TEXT
                )
            ''')

            # Task Force (Agency)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    title TEXT,
                    status TEXT DEFAULT 'pending', -- pending, done, archived
                    priority TEXT DEFAULT 'med', -- high, med, low
                    due_date TEXT,
                    created_at TEXT
                )
            ''')

            # Routing Events (Telemetry)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS routing_events (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    timestamp TEXT,
                    life_level TEXT,
                    complexity TEXT,
                    model_selected TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_est REAL,
                    auditor_score INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Strategic memory initialized (WAL enabled) at {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Failed to init Strategic Memory: {e}")

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def get_smart_context(self, user_id: int, current_query: str, token_limit: int = 2000) -> str:
        """
        Assemble a dynamic context prompt based on priority:
        1. User Profile (Values, Goals)
        2. Relevant Memories (RAG)
        3. Strategic Context (Recent Decisions)
        4. Recent History (Short-term)
        """
        parts = []
        current_tokens = 0
        
        # 1. User Profile (Highest Priority - ~200 tokens)
        profile_text = self._get_profile_text(user_id)
        if profile_text:
            parts.append(profile_text)
            current_tokens += len(profile_text) // 4 # Rough estimate
            
        # 2. RAG Context (Medium Priority - ~500-1000 tokens)
        # Allocate remaining budget mostly to RAG and History
        rag_budget = token_limit * 0.4 
        rag_docs = memory.search_memory(user_id, current_query, limit=5)
        notes = memory.search_notes(user_id, current_query, limit=3)
        
        rag_text = ""
        if rag_docs or notes:
            rag_text = "\n[RELEVANT MEMORIES & NOTES]\n"
            for doc in notes:
                rag_text += f"- 📌 {doc}\n"
            for doc in rag_docs:
                rag_text += f"- {doc}\n"
            
            # Simple truncation if too long
            if len(rag_text) // 4 > rag_budget:
                rag_text = rag_text[:int(rag_budget * 4)] + "..."
            
            parts.append(rag_text)
            current_tokens += len(rag_text) // 4

        # 3. Strategic Context (Recent Decisions/Insights)
        strat_text = self._get_strategic_summary(user_id, limit_decisions=2, limit_insights=2)
        if strat_text:
             parts.append(strat_text)
             current_tokens += len(strat_text) // 4

        # 4. Recent Conversation History is typically appended by the message handler 
        # as a separate list of messages, but if we need to summarize older history, do it here.
        # For now, we assume raw history is handled by main.py
        
        return "\n".join(parts)

    def _get_profile_text(self, user_id: int) -> str:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            p = cursor.fetchone()
            conn.close()
            
            if not p: return ""
            
            goals = json.loads(p["long_term_goals"]) if p["long_term_goals"] else []
            values = json.loads(p["core_values"]) if p["core_values"] else []
            
            if not goals and not values: return ""
            
            text = "[USER PROFILE]\n"
            if values: text += f"Values: {', '.join(values)}\n"
            if goals: text += f"Goals: {', '.join(goals)}\n"
            return text
        except Exception as e:
            logger.error(f"Error reading profile: {e}")
            return ""

    def _get_strategic_summary(self, user_id: int, limit_decisions=3, limit_insights=3) -> str:
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM strategic_decisions WHERE user_id = ? ORDER BY date DESC LIMIT ?", (user_id, limit_decisions))
            decisions = [dict(r) for r in cursor.fetchall()]
            
            cursor.execute("SELECT * FROM strategic_insights WHERE user_id = ? ORDER BY date DESC LIMIT ?", (user_id, limit_insights))
            insights = [dict(r) for r in cursor.fetchall()]
            
            conn.close()
            
            if not decisions and not insights: return ""
            
            text = "[STRATEGIC CONTEXT]\n"
            if decisions:
                text += "Recent Decisions:\n"
                for d in decisions:
                    outcome = d.get('expected_outcome') or d.get('decision', '')
                    text += f"- {d['topic']}: {outcome} ({d['date']})\n"
            
            if insights:
                text += "Recent Insights:\n"
                for i in insights:
                    text += f"- {i['type'].upper()}: {i['description']}\n"
                    
            return text
        except Exception as e:
            logger.error(f"Error reading strategic summary: {e}")
            return ""

    def load_memory(self, user_id: int) -> dict:
        """Legacy compatibility method"""
        # Re-implementation of load_memory logic using helper methods or direct DB access
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Profile
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            p = cursor.fetchone()
            profile = {
                "core_values": json.loads(p["core_values"]) if p and p["core_values"] else [],
                "long_term_goals": json.loads(p["long_term_goals"]) if p and p["long_term_goals"] else [],
                "decision_patterns": json.loads(p["decision_patterns"]) if p and p["decision_patterns"] else []
            }
            
            # Decisions
            cursor.execute("SELECT * FROM strategic_decisions WHERE user_id = ? ORDER BY date DESC", (user_id,))
            decisions = [dict(r) for r in cursor.fetchall()]
            for d in decisions:
                if d["tags"]: d["tags"] = json.loads(d["tags"])
            
            # Insights
            cursor.execute("SELECT * FROM strategic_insights WHERE user_id = ? ORDER BY date DESC", (user_id,))
            insights = [dict(r) for r in cursor.fetchall()]
            
            conn.close()
            return {
                "user_id": str(user_id),
                "profile": profile,
                "decisions": decisions,
                "insights": insights
            }
        except Exception as e:
            logger.error(f"❌ Error loading memory: {e}")
            return self.get_default_memory(user_id)

    def get_default_memory(self, user_id):
        return {
            "user_id": str(user_id),
            "profile": {"core_values": [], "long_term_goals": [], "decision_patterns": []},
            "decisions": [],
            "insights": []
        }

    async def process_interaction(self, user_id: int, user_input: str, bot_response: str, model: str):
        """
        Unified handler for processing a completed interaction.
        1. Save to Vector Store (memory.py)
        2. Save to Raw Log (SQLite)
        3. (Future) Trigger background digestion
        """
        # 1. Vector Store
        try:
            memory.save_interaction(user_id, user_input, bot_response, model)
        except Exception as e:
            logger.error(f"Vector save failed: {e}")

        # 2. Raw Log (legacy separate DB for now)
        # Note: main.py currently handles saving to 'messages' table in chat_history.db directly.
        # Ideally we move that here, but for now we keep the Separation of Concerns light.
        # We will assume main.py calls save_message_to_db separately or we can move it here.
        # For this refactor, let's keep it strictly 'Strategic' + 'Vector'.
        pass

    def add_decision(self, user_id: int, topic: str, context: str, rationale: str, outcome: str, status: str = 'active', tags: list = None):
        """Add a strategic decision"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            id = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute('''
                INSERT INTO strategic_decisions (id, user_id, date, topic, context, rationale, expected_outcome, status, tags, review_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id, user_id, date, topic, context, rationale, outcome, status, json.dumps(tags or []), date))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Add decision error: {e}")
            return False

    def add_insight(self, user_id: int, insight_type: str, description: str, evidence: str, recommendation: str):
        """Add an insight to SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            insight_id = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            date = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute('''
                INSERT INTO strategic_insights (id, user_id, date, type, description, evidence, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (insight_id, user_id, date, insight_type, description, evidence, recommendation))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ SQLite add_insight error: {e}")
            return False

    def update_profile(self, user_id: int, core_values: list = None, goals: list = None, patterns: list = None):
        """Upsert user profile"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get existing to merge? Or assume full overwrite for passed fields? 
            # The original code did merge by loading first.
            # Let's do an UPSERT logic more cleanly.
            
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            current_vals = json.loads(row[1]) if row and row[1] else []
            current_goals = json.loads(row[2]) if row and row[2] else []
            current_patterns = json.loads(row[3]) if row and row[3] else []
            
            new_vals = core_values if core_values is not None else current_vals
            new_goals = goals if goals is not None else current_goals
            new_patterns = patterns if patterns is not None else current_patterns
            
            cursor.execute('''
                INSERT INTO user_profiles (user_id, core_values, long_term_goals, decision_patterns)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    core_values=excluded.core_values,
                    long_term_goals=excluded.long_term_goals,
                    decision_patterns=excluded.decision_patterns
            ''', (user_id, json.dumps(new_vals), json.dumps(new_goals), json.dumps(new_patterns)))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Update profile error: {e}")
            return False

    def add_note(self, user_id: int, content: str, topic: str = "general") -> bool:
        """Add a note to persistent storage"""
        try:
            conn = self.get_connection()
            conn.execute(
                "INSERT INTO user_notes (id, user_id, topic, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), user_id, topic, content, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add note to DB: {e}")
            return False

    def get_notes(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Get recent notes from persistent storage"""
        try:
            conn = self.get_connection()
            rows = conn.execute(
                "SELECT * FROM user_notes WHERE user_id=? ORDER BY created_at DESC LIMIT ?", 
                (user_id, limit)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"❌ Failed to fetch notes from DB: {e}")
            return []

# Global Instance
global_memory = MemoryController()

# --- Public API Wrappers for Backward Compatibility ---

def init_memory_system():
    global_memory.init_db()

def load_memory(user_id: int):
    return global_memory.load_memory(user_id)

def get_strategic_context(user_id: int) -> str:
    # Use the new smart summary, but purely strategic parts
    return global_memory._get_strategic_summary(user_id)

def add_decision(user_id, *args, **kwargs):
    return global_memory.add_decision(user_id, *args, **kwargs)

def add_insight(user_id, *args, **kwargs):
    return global_memory.add_insight(user_id, *args, **kwargs)

def update_profile(user_id, *args, **kwargs):
    return global_memory.update_profile(user_id, *args, **kwargs)

async def get_smart_context(user_id, query):
    return await global_memory.get_smart_context(user_id, query)
