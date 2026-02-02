#!/bin/bash
# Clean restart - kills ALL python processes and starts fresh

echo "🧹 Clean Restart..."

# 1. Kill ALL python processes
echo "🛑 Killing all Python processes..."
killall -9 python3 2>/dev/null || true
killall -9 python 2>/dev/null || true

# 2. Wait
sleep 3

# 3. Verify no processes remain
REMAINING=$(ps aux | grep 'python.*main.py' | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  Still $REMAINING processes running, force killing..."
    ps aux | grep 'python.*main.py' | grep -v grep | awk '{print $2}' | xargs -r kill -9
    sleep 2
fi

# 4. Start bot
echo "🚀 Starting bot..."
cd /root/ai_assistant
bash start_bot.sh

# 5. Verify single instance
sleep 3
COUNT=$(ps aux | grep 'python.*main.py' | grep -v grep | wc -l)

if [ "$COUNT" -eq 1 ]; then
    echo "✅ Bot running (single instance)"
elif [ "$COUNT" -eq 0 ]; then
    echo "❌ Bot failed to start"
    tail -20 bot.log
else
    echo "⚠️  Multiple instances detected: $COUNT"
    ps aux | grep 'python.*main.py' | grep -v grep
fi
