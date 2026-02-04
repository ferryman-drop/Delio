
import asyncio
import os
import logging
from core.llm_service import call_actor
from core.tts_service import tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VisionVoiceTest")

async def test_voice():
    print("\n--- 🎙️ Testing Voice (TTS) ---")
    test_text = "Привіт! Це тестове повідомлення від системи Деліо. Голос Остапа активований."
    audio_path = await tts.generate_speech(test_text)
    if audio_path and os.path.exists(audio_path):
        size = os.path.getsize(audio_path) / 1024
        print(f"✅ Voice generated successfully: {audio_path} ({size:.2f} KB)")
    else:
        print("❌ Voice generation failed.")

async def test_vision():
    print("\n--- 👁️ Testing Vision (Gemini) ---")
    # Note: This requires a real image file. 
    # Since I don't have one, I will try to find any image in the project or just check the service setup.
    placeholder_path = "/root/ai_assistant/venv/lib/python3.12/site-packages/streamlit/static/favicon.png"
    
    if not os.path.exists(placeholder_path):
        # Retry with direct path if venv is different
        placeholder_path = "./venv/lib/python3.12/site-packages/streamlit/static/favicon.png"
    
    if not os.path.exists(placeholder_path):
        print(f"❌ No test image found. Please upload a real image to test Vision.")
        return

    try:
        resp, model = await call_actor(
            user_id=123,
            text="Що на цій картинці?",
            system_instruction="Ти експерт з аналізу зображень.",
            image_path=placeholder_path
        )
        print(f"✅ Vision Response ({model}): {resp}")
    except Exception as e:
        print(f"❌ Vision test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_voice())
    asyncio.run(test_vision())
