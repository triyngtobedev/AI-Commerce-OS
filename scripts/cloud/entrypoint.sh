#!/bin/sh
# Entrypoint para Railway/Render — processo foreground em PID 1.
set -e

cd /app

# Railway injeta PORT; fallback 8080 (não usar --workers: fork quebra detecção Active)
: "${PORT:=8080}"

echo "Starting uvicorn on 0.0.0.0:${PORT} (pid $$)"
exec uvicorn api.main_api:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --log-level info \
  --timeout-keep-alive 75
