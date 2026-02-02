#!/bin/bash
# Quick restart without killing all Python
cd /root/ai_assistant

echo "🛑 Stopping bot..."
pkill -9 -f "python.*main.py" || true
sleep 2

echo "🚀 Starting bot..."
source venv/bin/activate
nohup python main.py > bot.log 2>&1 &

sleep 3

if pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ Bot restarted"
    echo "📜 Logs: tail -f bot.log"
else
    echo "❌ Failed to start"
    tail -20 bot.log
fi
