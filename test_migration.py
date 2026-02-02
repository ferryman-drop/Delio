
import os
import sys
try:
    from google import genai
except ImportError:
    print("❌ Library 'google-genai' not found. Please run installation first.")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv("/root/ai_assistant/.env")

GEMINI_KEY = os.getenv("GEMINI_KEY")

def test_new_sdk():
    print(f"Testing google-genai SDK... Key: {GEMINI_KEY[:5]}...")
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents='Hello, are you the new SDK?'
        )
        print(f"✅ Success! Response: {response.text}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_new_sdk()
