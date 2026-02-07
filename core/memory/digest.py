
import logging
import json
import asyncio
from typing import Optional
from datetime import datetime
import config
from core.memory.funnel import funnel
from core.prompts.digestion import DIGESTION_SYSTEM

logger = logging.getLogger("Delio.Memory.Digest")

async def summarize_recent_history(user_id: int):
    """
    Analyzes the last 20 messages from Redis and updates Structured Memory.
    """
    logger.info(f"🌔 Starting Digestion for user {user_id}...")
    
    try:
        # 1. Fetch History from Redis
        history = await funnel.redis.get_history(user_id, limit=20)
        if not history:
            logger.info(f"ℹ️ No history to digest for user {user_id}")
            return
            
        # Format history for LLM
        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
        
        # 2. Call LLM (Gemini Flash for speed/cost)
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=config.GEMINI_KEY)
        
        prompt = f"""
        RECENT CHAT LOG:
        {history_text}
        
        Analyze this log and extract profile updates according to your instructions.
        """
        
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=config.MODEL_FAST,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=DIGESTION_SYSTEM,
                response_mime_type="application/json"
            )
        )
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            # Handle potential markdown wrapping
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
            
        # 3. Update Structured Memory
        # Extract facts
        facts = data.get("extracted_facts", [])
        for fact in facts:
            section = fact.get("section")
            key = fact.get("key")
            value = fact.get("value")
            confidence = fact.get("confidence", 0.5)
            
            if section and key and value:
                logger.info(f"💾 Digested Fact: {section}.{key} = {value}")
                await funnel.structured.set_memory(
                    user_id=user_id,
                    section=section,
                    key=key,
                    value=value,
                    confidence=confidence,
                    metadata={"source": "digestion_heartbeat"}
                )
        
        # Extract lessons (lessons_learned)
        lessons = data.get("lessons_learned", [])
        if lessons:
            # We could save these to a specific 'lessons' table or feedback section
            # For now, let's put them in 'feedback_signals'
            for idx, lesson in enumerate(lessons):
                 await funnel.structured.set_memory(
                     user_id=user_id,
                     section="feedback_signals",
                     key=f"lesson_{datetime.now().strftime('%Y%m%d')}_{idx}",
                     value=lesson,
                     confidence=0.7,
                     metadata={"source": "digestion_heartbeat"}
                 )

        logger.info(f"✅ Digestion complete for user {user_id}. Facts updated: {len(facts)}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Digestion failure for user {user_id}: {e}")
        return None
