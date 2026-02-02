
import os
from google import genai
from dotenv import load_dotenv

load_dotenv("/root/ai_assistant/.env")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def list_models():
    print("Listing models via google-genai SDK...")
    try:
        client = genai.Client(api_key=GEMINI_KEY)
        # Iterate over pages if necessary, but just printing first page usually enough
        for m in client.models.list(config={'page_size': 50}):
            print(f"- {m.name}")
            
    except Exception as e:
        print(f"❌ Error listing: {e}")

if __name__ == "__main__":
    list_models()
