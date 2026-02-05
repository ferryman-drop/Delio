# 🌧️ Delio (v4.1)

> **"Not just a bot. A Life OS."**

Delio is an advanced AI assistant framework designed for personal strategy, focus management, and intellectual resonance. It operates as a high-latency, persistent FSM (Finite State Machine) that doesn't just reply — it **thinks**, **plans**, and **acts**.

## 🧠 The Nucleus (Core Architecture)

*   **Triumvirate Intelligence**: Combines **Gemini 1.5 Pro** (Actor), **DeepSeek V3** (Critic), and **Claude 3.5 Sonnet** (Judge).
*   **Persistent Memory**: 
    *   Redis (Short-term context)
    *   ChromaDB (Long-term semantic recall)
    *   SQLite (Structured "Life Profile")
*   **State Machine**: A rigorous FSM (`IDLE` -> `THINK` -> `PLAN` -> `ACT`) prevents hallucination loops.

## ⭐ Key Features (Phase 4.1)

1.  **Resonance UX**: It feels alive. It pulses with a "Heartbeat" to check on you if you're silent.
2.  **Maturity Protocol**: Adapts to your level. Senior-level brevity by default. Use `/more` for deep dives.
3.  **Kernel Hardening**: 
    *   Trace IDs for every thought.
    *   Admin Alerts on Telegram for critical errors.
    *   Robust JSON parsing and memory budgeting.

## 🛠️ Deployment

```bash
# 1. Clone & Config
git clone https://github.com/ferryman-drop/delio-core.git
cp config.example.yaml config.yaml

# 2. Run with Docker
docker-compose up -d --build

# 3. Awaken
# Send /start in Telegram
```

## 📜 Documentation

- [Roadmap](docs/MASTER_ROADMAP.md) - The future of Delio.
- [Development Plan](docs/DEVELOPMENT_PLAN.md) - Current status.
- [Hardening Report](docs/TASK_014_HARDENING_REPORT.md) - Security details.

---
*Powered by Ferryman Drop.*
