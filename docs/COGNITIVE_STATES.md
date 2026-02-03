# 🔄 Module: Cognitive States (The Lifecycle)

This module contains the actual logic for each step of Delio's "thinking". Every file in `states/` represents a specialized node in the FSM.

## 📁 Key Files
- `states/observe.py`: Event parsing.
- `states/retrieve.py`: Context loading (via Funnel).
- `states/plan.py`: **Actor phase** (Gemini) + **Critic phase** (DeepSeek).
- `states/decide.py`: Plan finalization.
- `states/act.py`: Tool execution.
- `states/respond.py`: Telegram delivery.
- `states/reflect.py`: Self-improvement / Memory update.

## 🏃 Cognitive Cycle Breakdown

### 1. Plan (The Core Intelligence)
In this state, Gemini generates a response. If synergy mode is enabled, DeepSeek reviews the response:
- **Actor**: Proposes a draft.
- **Critic**: Analyzes the draft for logic, safety, and conciseness.
- **Output**: A validated, premium response.

### 2. Reflect (Post-Process)
After talking to the user, Delio doesn't stop. It looks back at the interaction:
- "Did I learn something new about the user?"
- "Was this a strategic decision we should log?"
- **Result**: New entries in `bot_data.db` (Goals, Insights).

## 💡 Clarification: The "Heartbeat" Event
Apart from user messages, the system triggers a `heartbeat` event every few hours. This enters the FSM at `RETRIEVE` to check for pending tasks or "proactive" check-ins (e.g., "Good morning, you have a deadline today").
