import logging
import os
import json
import uuid
from datetime import datetime
from openai import OpenAI
import memory_manager

logger = logging.getLogger(__name__)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_KEY")

class DeepSeekAuditor:
    def __init__(self):
        if DEEPSEEK_API_KEY:
            self.client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
        else:
            self.client = None

    async def audit_interaction(self, user_id: int, query: str, response: str, model_used: str):
        """
        Critique the interaction asynchronously.
        """
        if not self.client: return

        system_prompt = """
You are an AI Performance Auditor.
Analyze the interaction between User and AI Assistant.

Critique criteria:
1. Efficiency: Could it be shorter while retaining value? (1-10, 10=perfectly efficient).
2. Alignment: Does it sound like a Tier 1 strategic partner, not a generic chatbot?
3. Accuracy: Any obvious hallucinations or logic errors?

OUTPUT JSON ONLY:
{
  "efficiency_score": 1-10,
  "critique": "Short constructive feedback",
  "suggested_improvement": "Better version (optional)"
}
"""
        full_prompt = f"User: {query}\n\nAI ({model_used}): {response}"
        
        try:
            # Async call (via thread executor as client is sync, or asyncio if supported)
            # OpenAI client is sync by default. We should run in thread.
            import asyncio
            
            def _call():
                return self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt}
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )

            res = await asyncio.to_thread(_call)
            content = res.choices[0].message.content
            data = json.loads(content)
            
            # Save to DB
            self._save_audit(user_id, query, response, data, model_used)
            logger.info(f"🧐 Audit Complete: Score {data.get('efficiency_score')}/10")
            
        except Exception as e:
            logger.error(f"❌ Audit Failed: {e}")

    def _save_audit(self, user_id, query, resp, data, model_used):
        try:
            conn = memory_manager.MemoryController().get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_logs (id, user_id, date, query, response, efficiency_score, critique, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                user_id,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                query,
                resp,
                data.get("efficiency_score", 0),
                json.dumps(data), # Store full JSON in critique/payload column or split
                model_used
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Failed to save audit log: {e}")

auditor_instance = DeepSeekAuditor()
