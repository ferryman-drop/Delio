import sys
sys.path.append("/root/ai_assistant")
import os
from google import genai
from config import GEMINI_KEY

client = genai.Client(api_key=GEMINI_KEY)

try:
    print("Listing models...")
    for m in client.models.list():
        if "embed" in m.name:
            print(f"Model: {m.name}")
            print(f"Supported methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")
