import logging
import sqlite3
import config
from datetime import datetime

logger = logging.getLogger(__name__)

async def explain_last_interaction(user_id: int):
    """
    Analyzes the last interaction from audit_logs and explains WHY the bot replied that way.
    """
    import memory_manager
    conn = memory_manager.MemoryController().get_connection()
    try:
        # 1. Fetch last audit log (contains full Query & Response)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT query, response, model_used, efficiency_score, critique, date 
            FROM audit_logs 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT 1
        ''', (user_id,))
        
        row = cursor.fetchone()
        
        if not row:
            return "🤷‍♂️ I don't see any recent conversations to explain."
            
        query, response, model, score, critique_json, date = row
        
        # 2. Get recent memory context context (Simulate what the bot saw)
        # In a perfect world, we'd log the exact context used. 
        # For MVP, we'll ask the Explainer Model to infer based on the output.
        
        # 3. Construct Analysis Prompt
        prompt = f"""
Ти — модуль пояснюваності штучного інтелекту (AI Explainability Engine).
Твоє завдання — пояснити, ЧОМУ Асистент дав саме таку відповідь користувачу.

КОНТЕКСТ:
- ID користувача: {user_id}
- Час: {date}
- Модель: {model}
- Оцінка аудитора: {score}/10

ВЗАЄМОДІЯ:
Користувач: "{query}"
Асистент: "{response}"

ЗАВДАННЯ:
Поясни логіку Асистента прозоро, у стилі "за лаштунками".
Опиши українською мовою:
1. Інтенція: Що насправді хотів користувач?
2. Стратегія: Чому Асистент обрав такий тон/довжину?
3. Пам'ять: Чи використовував він (ймовірно) якісь особисті факти?

Формат виводу: Markdown (короткий абзац + пункти). Почни з "🕵️ **Аналіз:**"
"""

        # 4. Call Small Model (Flash) - New SDK
        from google import genai
        client = genai.Client(api_key=config.GEMINI_KEY)
        result = client.models.generate_content(
            model=config.MODEL_FAST,  # Flash Lite 2.0
            contents=prompt
        )
        
        return result.text

    except Exception as e:
        logger.error(f"Explain Error: {e}")
        return f"❌ Failed to explain: {e}"
    finally:
        conn.close()
