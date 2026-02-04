
import asyncio
import os
import logging
import config
from core.llm_service import call_judge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClaudeTest")

async def test_claude():
    print("\n--- ⚔️ Testing Claude 3.5 Sonnet (The Judge) ---")
    
    user_query = "Привіт! Хто ти і яка твоя роль у системі Delio?"
    actor_response = "Я Delio, твій помічник. Я допомагаю тобі з задачами."
    instruction = "Ти — Delio, професійний Life OS Mentor. Твій тон має бути надихаючим та професійним."

    try:
        final_resp, label = await call_judge(
            user_query=user_query,
            actor_response=actor_response,
            instruction=instruction
        )
        print(f"✅ Judge Label: {label}")
        print(f"✅ Judge Response: {final_resp}")
        
        if "🧠" in label:
            print("\n🌟 SUCCESS: Claude integration is working!")
        else:
            print("\n❌ FAILURE: Claude not detected in response label.")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    # Ensure config can find the key
    os.environ["ANTHROPIC_KEY"] = "REDACTED_KEY"
    # Overwrite config's value for the test specifically
    import config
    config.ANTHROPIC_KEY = os.environ["ANTHROPIC_KEY"]
    
    asyncio.run(test_claude())
