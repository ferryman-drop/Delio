# 🧠 Module: Memory Funnel & Context layers

Delio doesn't just "see" the last message. It pulls from three distinct layers of time and structure to build a "Smart Context".

## 📁 Key Files
- `core/memory/funnel.py`: Aggregation logic (`ContextFunnel`).
- `legacy/old_memory.py`: ChromaDB Vector Search (Long-term).
- `legacy/memory_manager_v2.py`: SQLite Structured Memory (Life OS stats).
- `data/bot_data.db`: The core persistence layer.

## 🧱 The Three Layers
1. **Short-Term (Redis)**: The last 10 messages of the current dialogue. Fluid, fast, and prone to "forgetting" once the topic changes.
2. **Long-Term (Vector)**: Semantic search across the entire history of the chat. "Find that time we talked about solar energy in January."
3. **Structured (Life OS)**: High-confidence facts (Name, Goals, Core Values, Resources). This is the "User Profile" that defines Delio's mentor persona.

## 🌪️ The Funnel Logic
The `ContextFunnel` takes the raw user input and simultaneously queries all layers. It then flattens them into a structured prompt for the **Actor (PLAN state)**:
```text
[IDENTITY] ...
[RECENT MESSAGES] ...
[RELEVANT MEMORIES] ...
[STRUCTURED PROFILE] ...
[USER INPUT] ...
```

## 📊 Clarification: Context Compression
When the history gets too long, the `RETRIEVE` state triggers a summarization step, ensuring we never hit the LLM's token limit while preserving critical context.
