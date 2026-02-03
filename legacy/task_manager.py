import logging
import uuid
import sqlite3
from datetime import datetime
import memory_manager

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.mem_ctrl = memory_manager.global_memory

    def add_task(self, user_id, title, priority='med', due_date=None):
        """Add a new task."""
        task_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        conn = self.mem_ctrl.get_connection()
        try:
            conn.execute('''
                INSERT INTO tasks (id, user_id, title, status, priority, due_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, user_id, title, 'pending', priority, due_date, created_at))
            conn.commit()
            logger.info(f"✅ Task Added: {title} ({user_id})")
            return task_id
        except Exception as e:
            logger.error(f"❌ Add Task Error: {e}")
            return None
        finally:
            conn.close()

    def list_tasks(self, user_id, status='pending', limit=10):
        """List tasks filter by status."""
        conn = self.mem_ctrl.get_connection()
        try:
            if status == 'all':
                query = "SELECT id, title, priority, due_date, status FROM tasks WHERE user_id=? ORDER BY created_at DESC LIMIT ?"
                params = (user_id, limit)
            else:
                query = "SELECT id, title, priority, due_date, status FROM tasks WHERE user_id=? AND status=? ORDER BY created_at DESC LIMIT ?"
                params = (user_id, status, limit)
                
            rows = conn.execute(query, params).fetchall()
            return [{"id": r[0], "title": r[1], "priority": r[2], "due": r[3], "status": r[4]} for r in rows]
        finally:
            conn.close()

    def complete_task(self, user_id, task_identifier):
        """
        Complete a task by ID or mostly matching Title.
        Returns the completed task title or None.
        """
        conn = self.mem_ctrl.get_connection()
        try:
            # Try ID match first
            row = conn.execute("SELECT id, title FROM tasks WHERE id=? AND user_id=?", (task_identifier, user_id)).fetchone()
            
            if not row:
                # Try fuzzy title match
                row = conn.execute("SELECT id, title FROM tasks WHERE title LIKE ? AND user_id=? AND status='pending'", (f"%{task_identifier}%", user_id)).fetchone()
            
            if row:
                t_id, title = row
                conn.execute("UPDATE tasks SET status='done' WHERE id=?", (t_id,))
                conn.commit()
                logger.info(f"✅ Task Completed: {title}")
                return title
            return None
        finally:
            conn.close()

    def get_due_soon(self, minutes=60):
        """Get tasks due within N minutes."""
        # This requires datetime parsing in SQL or Python. Simplified for text dates:
        # We'll just fetch all pending with a due date and check in python
        # (Not efficient for millions of tasks, fine for personal OS)
        conn = self.mem_ctrl.get_connection()
        try:
            rows = conn.execute("SELECT id, user_id, title, due_date FROM tasks WHERE status='pending' AND due_date IS NOT NULL").fetchall()
            due_soon = []
            now = datetime.now()
            for r in rows:
                try:
                    # simplistic ISO parse, might need adjustment based on input format
                    # Assumes YYYY-MM-DD HH:MM:SS or ISO
                    dt = datetime.fromisoformat(r[3])
                    diff = (dt - now).total_seconds() / 60
                    if 0 < diff <= minutes:
                        due_soon.append({"id": r[0], "user_id": r[1], "title": r[2], "due": r[3]})
                except: pass
            return due_soon
        finally:
            conn.close()

# Global Instance
task_system = TaskManager()
