#!/bin/bash
# Life OS Bot Deployment Script
# Ensures only ONE instance runs

set -e

echo "🚀 Deploying Life OS Bot..."

# 1. Kill ALL existing bot processes
echo "🔪 Killing existing processes..."
pkill -9 -f "python.*main.py" || true
sleep 2

# 2. Verify all dead
REMAINING=$(ps aux | grep "python.*main.py" | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "❌ WARNING: $REMAINING processes still running!"
    ps aux | grep "python.*main.py" | grep -v grep
    exit 1
fi

# 3. Install systemd service
echo "📦 Installing systemd service..."
sudo cp /root/ai_assistant/delio_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable delio_bot

# 4. Start bot
echo "▶️  Starting bot..."
sudo systemctl start delio_bot

# 5. Check status
sleep 3
sudo systemctl status delio_bot --no-pager

# 6. Show recent logs
echo ""
echo "📋 Recent logs:"
sudo journalctl -u delio_bot -n 20 --no-pager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📌 Useful commands:"
echo "  Status:  sudo systemctl status delio_bot"
echo "  Logs:    sudo journalctl -u delio_bot -f"
echo "  Restart: sudo systemctl restart delio_bot"
echo "  Stop:    sudo systemctl stop delio_bot"
