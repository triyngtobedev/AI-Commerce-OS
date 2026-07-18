#!/usr/bin/env bash
# Inicia a API FastAPI de integração n8n
#
# Uso:
#   chmod +x api/run_api.sh
#   ./api/run_api.sh
#
# Variáveis opcionais:
#   API_HOST (padrão: 0.0.0.0)
#   API_PORT (padrão: 8000)
#   API_WORKERS (padrão: 1 — necessário para asyncio.Event no job_store)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Carrega .env principal se existir
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
WORKERS="${API_WORKERS:-1}"

echo "Starting AI-Commerce-OS Pipeline API on ${HOST}:${PORT} (workers=${WORKERS})"

exec uvicorn api.main_api:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "$WORKERS" \
  --log-level info
