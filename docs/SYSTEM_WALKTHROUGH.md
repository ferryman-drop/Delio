# 🚶 AID Migration Walkthrough: From Script to Kernel

This document tracks the evolution of Delio from a sequential script to a robust, state-managed **AI Kernel (AID)**.

## 🏁 Phase 0: The "Legacy" Era
Originally, Delio was a complex asynchronous script. Handlers directly called AI models, which then directly called tools.
- **Problem**: "Hallucinated" tool calls, unpredictable loops, fragile context handling.
- **Solution**: Complete architectural overhaul into a **Finite State Machine (FSM)**.

## 🏗️ Phase 1: The FSM Infrastructure (Observe/Respond)
We defined the first states. Instead of "answering a message", the system now "processes an event".
- **Observe**: Capture Telegram input, detect file types, extract meta-data.
- **Respond**: Pure delivery state. Decoupled from logic.

## 🧠 Phase 2: Context Funnel (The Memory Consolidation)
We realized memory was scattered. We built the `ContextFunnel`.
- **Retrieval**: Unified search across Redis (Recent), ChromaDB (Long-term), and SQLite (Structured facts).
- **Invariance**: Memory retrieval is now a dedicated state, ensuring the LLM has full context before "thinking".

## ⚖️ Phase 3: Actor-Critic & State Guard (Safety)
The most critical part of the 3.0 update.
- **Actor (Gemini)**: Proposes plans and content.
- **Critic (DeepSeek)**: Validates the output, checks for logic errors or safety violations.
- **State Guard**: A runtime hypervisor that blocks any tool call (bash, file write) unless the system is in the authorized `ACT` state.

## 🔄 The Cognitive Cycle (Observe → Reflect)
Every user message now triggers this cycle:
1. **Observe**: "What did the user just say?"
2. **Retrieve**: "What do I know about this?"
3. **Plan**: "Gemini, what should we do?"
4. **Decide**: "DeepSeek, is this plan safe and logical?"
5. **Act**: "Execute tools if needed."
6. **Respond**: "Talk to the user."
7. **Reflect**: "What did I learn? Update long-term memory."

---
## 💡 Clarification: Why this structure?
- **Stability**: If the AI crashes in `ACT`, the `State Guard` ensures it doesn't leave half-written files or open processes.
- **Scalability**: Want to add "Image Generation"? Just add a new `VisionState` and a transition rule.
- **Transparency**: Every action has a `Trace` (Observe -> Plan -> ...), which you can see in `/agent`.

---
*Status: AID v3.0 Migration COMPLETE.*
