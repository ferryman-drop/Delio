#!/bin/bash
# 💊 BERIBERI: The Watchdog for Delio (V2)
# Checks health and restarts main.py if needed.

# Config
ROOT_DIR="/root/ai_assistant"
LOG_FILE="$ROOT_DIR/logs/watchdog.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$DATE] $1" >> "$LOG_FILE"
    echo "[$DATE] $1"
}

check_services() {
    # Check if main.py process exists
    # We use -f to match the command line including the file name
    if ! pgrep -f "venv/bin/python main.py" > /dev/null; then
        log "❌ main.py process NOT found."
        return 1
    fi

    # Since main.py is a bot, we don't have an HTTP health check.
    # Future enhancement: Check bot responsiveness via a separate health-tool if needed.

    return 0
}

restart_all() {
    log "🔄 RESTARTING DELIO SYSTEM..."
    
    # Use the official start script
    cd "$ROOT_DIR"
    bash scripts/start_bot.sh
    
    log "✅ Restart command sent via start_bot.sh"
}

# MAIN LOOP
if check_services; then
    # All good
    logger -t beriberi "Delio is healthy"
    exit 0
else
    restart_all
fi
