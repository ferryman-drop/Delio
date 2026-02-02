
import asyncio
import os
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv("/root/ai_assistant/.env")

# Config
GEMINI_KEY = os.getenv("GEMINI_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")

async def test_gemini():
    print(f"Testing Gemini... Key: {GEMINI_KEY[:5]}...")
    try:
        genai.configure(api_key=GEMINI_KEY)
        # UPDATED: Use the correct model name
        model = genai.GenerativeModel("gemini-1.5-flash") 
        resp = model.generate_content("Hello, are you online?")
        print(f"✅ Gemini OK: {resp.text[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Gemini Failed: {e}")
        return False

async def test_deepseek():
    print(f"Testing DeepSeek... Key: {DEEPSEEK_KEY[:5]}...")
    try:
        client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print(f"✅ DeepSeek OK: {resp.choices[0].message.content[:50]}...")
        return True
    except Exception as e:
        print(f"❌ DeepSeek Failed: {e}")
        return False

async def main():
    print("--- STARTING CONNECTION TEST ---")
    g = await test_gemini()
    d = await test_deepseek()
    
    if g and d:
        print("\n🎉 SYNERGY READY: Both models are online.")
    elif g or d:
        print("\n⚠️ PARTIAL SYNERGY: One model is down.")
    else:
        print("\n💀 SYSTEM BLACKOUT: Both models failed.")

if __name__ == "__main__":
    asyncio.run(main())
