
import os
import logging
import sqlite3
from functools import wraps
from aiogram import types

logger = logging.getLogger(__name__)

# Role definitions
ROLE_ADMIN = "admin"
ROLE_USER = "user"
ROLE_GUEST = "guest"

# Admin from environment
ADMIN_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

# Database path
DB_PATH = os.path.join(os.getcwd(), "data", "bot_data.db")

def init_roles_db():
    """Initialize roles table in database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id INTEGER PRIMARY KEY,
                role TEXT DEFAULT 'user',
                granted_by INTEGER,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add admin from env if not exists
        if ADMIN_ID > 0:
            cursor.execute('''
                INSERT OR IGNORE INTO user_roles (user_id, role, granted_by)
                VALUES (?, ?, ?)
            ''', (ADMIN_ID, ROLE_ADMIN, ADMIN_ID))
        
        conn.commit()
        conn.close()
        logger.info("✅ Roles database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to init roles DB: {e}")

def get_user_role(user_id: int) -> str:
    """Get user role from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT role FROM user_roles WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # Default: new users are 'user'
        return ROLE_USER
    except Exception as e:
        logger.error(f"❌ Error getting role for {user_id}: {e}")
        return ROLE_USER

def set_user_role(user_id: int, role: str, granted_by: int):
    """Set user role"""
    if role not in [ROLE_ADMIN, ROLE_USER, ROLE_GUEST]:
        raise ValueError(f"Invalid role: {role}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_roles (user_id, role, granted_by)
            VALUES (?, ?, ?)
        ''', (user_id, role, granted_by))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Set role {role} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error setting role: {e}")
        return False

def is_admin(user_id: int) -> bool:
    """Quick check if user is admin"""
    return get_user_role(user_id) == ROLE_ADMIN

def revoke_role(user_id: int):
    """Reset user to default 'user' role"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Revoked custom role for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error revoking role: {e}")
        return False

def get_all_users():
    """Get all users with roles"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, role, granted_at FROM user_roles ORDER BY granted_at DESC')
        results = cursor.fetchall()
        conn.close()
        
        return results
    except Exception as e:
        logger.error(f"❌ Error getting users: {e}")
        return []

def require_role(required_role: str):
    """Decorator to check user role before executing command"""
    def decorator(func):
        @wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            user_id = message.from_user.id
            user_role = get_user_role(user_id)
            
            # Role hierarchy: admin > user > guest
            role_hierarchy = {ROLE_ADMIN: 3, ROLE_USER: 2, ROLE_GUEST: 1}
            
            user_level = role_hierarchy.get(user_role, 0)
            required_level = role_hierarchy.get(required_role, 0)
            
            if user_level >= required_level:
                return await func(message, *args, **kwargs)
            else:
                await message.answer(
                    f"❌ Доступ заборонено.\n"
                    f"Ваша роль: {user_role}\n"
                    f"Потрібна роль: {required_role} або вище"
                )
                logger.warning(f"⚠️ User {user_id} ({user_role}) tried to access {required_role} command")
        
        return wrapper
    return decorator
