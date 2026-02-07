#!/bin/bash
# 🧹 Delio Total Reset Script (v5.0 Hard Reset)

echo "🛑 Stopping all Delio services (Aggressive)..."
pkill -9 -f "python3 server.py"
pkill -9 -f "python3 client/bot.py"
pkill -9 -f "python3 scripts/obsidian_sync.py"
fuser -k 8000/tcp # Kill anything on port 8000
sleep 2

echo "🗑️ Wiping SQL Databases..."
rm -f /root/ai_assistant/data/bot_data.db
rm -f /root/ai_assistant/data/chat_history.db
rm -f /root/ai_assistant/data/routing_weights.json

echo "🗑️ Wiping Vector Database (ChromaDB)..."
rm -rf /root/ai_assistant/data/chroma_db/*

echo "🗑️ Clearing Logs..."
rm -rf /root/ai_assistant/logs/*.log
rm -rf /root/ai_assistant/logs/*.json

echo "♻️ Resetting User States in StateGuard..."
# This is handled by Crash Amnesia logic in the bot startup, 
# but we've wiped the source DB and memory, so it's clean.

echo "✅ System Reset to ZERO."
echo "🚀 Restarting via Watchdog..."
./scripts/beriberi.sh
