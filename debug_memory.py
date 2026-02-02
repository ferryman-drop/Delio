
import memory
import sys
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))

def check_memory():
    user_id = 403314201
    query = "Claude"
    results = memory.search_memory(user_id, query)
    print(f"Query: {query}")
    print(f"Results: {results}")

    query = "Яка ти модель"
    results = memory.search_memory(user_id, query)
    print(f"Query: {query}")
    print(f"Results: {results}")

if __name__ == "__main__":
    memory.init_memory()
    check_memory()
