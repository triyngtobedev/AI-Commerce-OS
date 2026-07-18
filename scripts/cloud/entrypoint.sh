#!/bin/sh
# Entrypoint para Railway/Render — usa PORT injetado pela plataforma.
set -e

PORT="${PORT:-8000}"
echo "Starting uvicorn on 0.0.0.0:${PORT}"
exec uvicorn api.main_api:app --host 0.0.0.0 --port "${PORT}" --workers 1
