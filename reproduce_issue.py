
import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

async def reproduce():
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_KEY"),
        base_url="https://api.deepseek.com"
    )
    
    # EXACT same prompt as in the logs for Ferryman (ID 35)
    # Default system prompt from config.yaml + Friendly Helper persona (none/default)
    
    system_prompt = """# ЕЛІТНИЙ МЕНТОР-СТРАТЕГ
Прийми роль елітного професійного ментора... (shortened for brevity in reproduction script)
"""
    # Actually let's use the one from config.yaml
    
    identity_prompt = f"\n\n[IDENTITY]\nТвій поточний ID користувача: 403314201\nТи зараз працюєш на моделі: DEEPSEEK.\nТи НЕ можеш змінювати модель через інструменти, але користувач може написати /model для цього.\n"
    
    full_prompt = system_prompt + "\n\nRelevant memories:\n\n" + identity_prompt
    
    print("--- SENDING QUERY ---")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": "Яка ти модель?"}
        ]
    )
    print(f"Response: {response.choices[0].message.content}")

if __name__ == "__main__":
    asyncio.run(reproduce())
