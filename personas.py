
import os
import logging
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.getcwd(), "data", "bot_data.db")
PERSONAS_DIR = os.path.join(os.getcwd(), "personas")

# Available personas
PERSONAS = {
    "technical_expert": "🔧 Технічний Експерт",
    "friendly_helper": "😊 Дружній Помічник",
    "teacher": "📚 Вчитель",
    "creative_writer": "✍️ Креативний Письменник",
    "business_consultant": "💼 Бізнес Консультант",
    "elite_mentor": "🎯 Elite Mentor-Strategist"
}

def init_personas_db():
    """Initialize personas table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_personas (
                user_id INTEGER PRIMARY KEY,
                persona TEXT DEFAULT 'friendly_helper',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Personas database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to init personas DB: {e}")

def get_user_persona(user_id: int) -> str:
    """Get user's current persona"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT persona FROM user_personas WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        
        # Default persona
        return "friendly_helper"
    except Exception as e:
        logger.error(f"❌ Error getting persona for {user_id}: {e}")
        return "friendly_helper"

def set_user_persona(user_id: int, persona: str) -> bool:
    """Set user's persona"""
    if persona not in PERSONAS:
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_personas (user_id, persona, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, persona))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Set persona {persona} for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error setting persona: {e}")
        return False

def load_persona_prompt(persona: str) -> str:
    """Load persona system prompt from file"""
    try:
        filepath = os.path.join(PERSONAS_DIR, f"{persona}.md")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning(f"⚠️ Persona file not found: {filepath}")
            return ""
    except Exception as e:
        logger.error(f"❌ Error loading persona: {e}")
        return ""

def get_persona_system_prompt(user_id: int) -> str:
    """Get full system prompt with user's persona"""
    persona = get_user_persona(user_id)
    persona_content = load_persona_prompt(persona)
    
    if persona_content:
        return f"{persona_content}\n\n---\n\nВідповідайте користувачу згідно з цією роллю."
    else:
        return "Ви - корисний AI асистент."
