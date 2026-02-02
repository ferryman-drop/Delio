
import os
import sys
import logging

# Add project root to path
sys.path.append('/root/ai_assistant')

# Load env vars
from dotenv import load_dotenv
load_dotenv('/root/ai_assistant/.env')

import google.generativeai as genai
import memory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_memory():
    # 1. Setup
    api_key = os.getenv("GEMINI_KEY")
    if not api_key:
        print("❌ GEMINI_KEY not found")
        return
    
    genai.configure(api_key=api_key)
    memory.init_memory()
    
    user_id = 999999 # Test user
    
    # 2. Add memories
    print("💾 Saving memories...")
    import time
    memory.save_interaction(user_id, "Мене звати Тестовий Користувач.", "Привіт, Тестовий Користувач!", "TestModel")
    time.sleep(1)
    memory.save_interaction(user_id, "Я люблю програмувати на Python.", "Python - чудова мова!", "TestModel")
    time.sleep(1)
    memory.save_interaction(user_id, "Мій улюблений фрукт - яблуко.", "Яблука корисні.", "TestModel")
    time.sleep(1)
    
    # 3. Search
    print("🔍 Searching for 'What is my name?'...")
    results_name = memory.search_memory(user_id, "Як мене звати?", limit=3)
    print(f"Result: {results_name}")
    
    print("🔍 Searching for 'favorite fruit'...")
    results_fruit = memory.search_memory(user_id, "Що я люблю їсти?", limit=3)
    print(f"Result: {results_fruit}")
    
    # 4. Verify
    if any("Тестовий Користувач" in r for r in results_name) and \
       any("яблуко" in r for r in results_fruit):
        print("✅ RAG Verification PASSED!")
    else:
        print("❌ RAG Verification FAILED (Context missing)")

if __name__ == "__main__":
    test_memory()
