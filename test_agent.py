
import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv
import tools

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))

async def test_agent():
    print("Testing Gemini Agent with autonomous tools...")
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        tools=tools.TOOLS_LIST,
        system_instruction="Ти - стратегічний асистент. Використовуй пошук якщо не знаєш відповіді."
    )
    
    chat = model.start_chat(enable_automatic_function_calling=True)
    
    # Question that requires search
    print("Asking: 'Хто зараз лідирує в Australian Open 2026?'")
    response = chat.send_message("Хто зараз лідирує в Australian Open 2026?")
    
    print("\n--- Model Response ---")
    print(response.text)
    
    print("\n--- Tool History ---")
    for turn in chat.history:
        for part in turn.parts:
            if part.function_call:
                print(f"🛠️ Tool called: {part.function_call.name}")
            if part.function_response:
                print(f"📦 Tool result received for: {part.function_response.name}")

if __name__ == "__main__":
    asyncio.run(test_agent())
