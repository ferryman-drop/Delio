
import sys
import logging
from router import classify_intent, INTENT_FAST, INTENT_REASONING, configure_router
import os
from dotenv import load_dotenv

# Setup
sys.path.append('/root/ai_assistant')
load_dotenv('/root/ai_assistant/.env')
logging.basicConfig(level=logging.INFO)

def test_router():
    api_key = os.getenv("GEMINI_KEY")
    configure_router(api_key)
    
    test_cases = [
        ("Привіт", INTENT_FAST),
        ("Hello world", INTENT_FAST),
        ("Help", INTENT_FAST),
        ("Напиши код на Python для сортування", INTENT_REASONING),
        ("Analyze this text complexity", INTENT_REASONING),
        ("Create a docker-compose.yml", INTENT_REASONING),
        ("Ok", INTENT_FAST),
    ]
    
    passed = 0
    for query, expected in test_cases:
        result = classify_intent(query)
        icon = "✅" if result == expected else "❌"
        print(f"{icon} Query: '{query}' -> Got: {result} (Expected: {expected})")
        if result == expected:
            passed += 1
            
    print(f"\nScore: {passed}/{len(test_cases)}")
    if passed == len(test_cases):
        print("🎉 Router Verification PASSED!")
    else:
        print("⚠️ Router Verification FAILED")

if __name__ == "__main__":
    test_router()
