# 🧬 Life OS Assistant - User Manual

## 🚀 Quick Start
To launch the entire system (Bot + Dashboard + Database):

```bash
docker-compose up -d --build
```

Access the **Dashboard** at: `http://localhost:8501`

## 🧩 Components
1.  **AI Assistant**: Running in `main.py`. Connects to Telegram.
    - **Models**: Auto-switches between `Gemini 1.5 Flash` (Fast) and `Gemini 1.5 Pro` (Smart) based on task complexity.
    - **Auditor**: DeepSeek reviews every answer in the background.
    - **Memory**: Stores insights in `data/bot_data.db`.

2.  **Dashboard**: Running in `dashboard.py`.
    - **Life Level**: View your current XP and Level.
    - **Timeline**: See your strategic decision history.
    - **Health**: Monitor the AI's efficiency scores.

## 🛠️ Configuration
- Keys are in `.env`.
- To change models, edit `main.py` or `.env`.

## 🕒 Proactivity
The bot will send you a **Morning Briefing** (based on previous day's insights) automatically at 04:00 AM (UTC).
