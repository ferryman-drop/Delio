#!/bin/bash
set -e

echo "🚀 Starting Delio Assistant (Python Mode)..."

cd /root/ai_assistant

# 1. Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate venv
echo "✅ Activating virtual environment..."
source venv/bin/activate

# 3. Install/Update dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# 4. Stop old process if running (aggressive)
echo "🛑 Stopping old processes..."
pkill -9 -f "python.*main.py" || true
sleep 2
# Double-check and kill any remaining
ps aux | grep 'python.*main.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9 || true
sleep 1

# 5. Start bot
echo "🔥 Starting bot..."
nohup /root/ai_assistant/venv/bin/python main.py > bot.log 2>&1 &

sleep 2

# 6. Check status
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Bot started successfully!"
    echo "📜 View logs: tail -f bot.log"
    echo "🛑 Stop bot: pkill -f 'python main.py'"
else
    echo "❌ Bot failed to start. Check bot.log"
    tail -20 bot.log
fi
