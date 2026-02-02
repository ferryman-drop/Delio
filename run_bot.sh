#!/bin/bash
echo "🚀 Starting Delio Assistant..."

# Check if docker compose exists
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    echo "✅ Docker Compose (v2) found."
    docker compose up -d --build
    echo "📜 Logs:"
    docker compose logs -f
    exit 0
fi

if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose (v1) found."
    docker-compose up -d --build
    echo "📜 Logs:"
    docker-compose logs -f
    exit 0
fi

echo "⚠️ Docker Compose not found. Trying local Python..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found."
    exit 1
fi

# Setup Venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual env..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "dwm Installing requirements..."
pip install -r requirements.txt

echo "🔥 Running Bot..."
python3 main.py
