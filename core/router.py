import logging
import asyncio
import config
from google import genai
from typing import Literal

logger = logging.getLogger("Delio.Router")

class IntentRouter:
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_KEY)
        self.model = config.MODEL_FAST # Usually Gemini 1.5 Flash
        
    async def classify(self, text: str) -> Literal["SIMPLE", "COMPLEX"]:
        """
        Classifies user intent into SIMPLE (direct answer) or COMPLEX (requires tools/critic).
        """
        prompt = f"""
        Analyze the following user message and classify it as either SIMPLE or COMPLEX.
        
        - SIMPLE: Basic greeting, small talk, simple question that doesn't need external data or deep reasoning.
        - COMPLEX: Needs search, reminders, file access, multi-step planning, or strategic advice.
        
        User message: "{text}"
        
        Return ONLY the word: SIMPLE or COMPLEX.
        """
        
        try:
            # We use a synchronous call in the first version, or wrap in thread
            # Better to use the async version of the SDK if available or run_in_executor
            # But for simplicity and speed (Flash is fast), simple call:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt
            )
            
            result = response.text.strip().upper()
            if "COMPLEX" in result:
                return "COMPLEX"
            return "SIMPLE"
            
        except Exception as e:
            logger.error(f"Router Classification Error: {e}")
            return "COMPLEX" # Fallback to safe mode

router = IntentRouter()
