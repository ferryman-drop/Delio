#!/usr/bin/env bash
set -euo pipefail

# Скрипт для розгортання Ollama у docker-compose та завантаження Llama 3.2-1B
# Використання:
#   chmod +x scripts/deploy_ollama.sh
#   ./scripts/deploy_ollama.sh [MODEL_NAME]

MODEL=${1:-llama3.2:1b}
COMPOSE_FILE="docker-compose.yml"
SERVICE_NAME=ollama
CONTAINER_NAME=ai_assistant_ollama

echo "[+] Deploy Ollama service via docker-compose (service: $SERVICE_NAME)"

# Check docker availability
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не знайдено. Установіть Docker і retry. Інструкція: https://docs.docker.com/engine/install/"
  exit 2
fi

# Check docker-compose or docker compose
if command -v docker-compose >/dev/null 2>&1; then
  DC_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  DC_CMD="docker compose"
else
  echo "docker-compose не знайдено. Встановіть docker-compose або оновіть Docker CLI." >&2
  exit 2
fi

# Start only the ollama service
echo "[+] Starting $SERVICE_NAME via $DC_CMD"
$DC_CMD up -d $SERVICE_NAME

# Wait for container to be running
echo "[+] Waiting for container $CONTAINER_NAME to be running..."
for i in {1..30}; do
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "[+] Container running"
    break
  fi
  sleep 1
done

# Try to pull model using ollama CLI inside container (if available)
if docker exec $CONTAINER_NAME ollama version >/dev/null 2>&1; then
  echo "[+] ollama CLI found in container, pulling model: $MODEL"
  docker exec $CONTAINER_NAME ollama pull $MODEL || {
    echo "[!] Pull failed. Check model name or container logs."
  }
  echo "[+] Model pull attempted. Check 'docker logs $CONTAINER_NAME' for details."
else
  echo "[!] ollama CLI not found in container. If this is a managed Ollama image, follow manual steps:" 
  echo "  1) Exec into container: docker exec -it $CONTAINER_NAME /bin/sh"
  echo "  2) Run: ollama pull $MODEL"
fi

echo "[+] Done. If model download succeeded, Ollama should expose the service on port 11434 (configured in docker-compose)."
