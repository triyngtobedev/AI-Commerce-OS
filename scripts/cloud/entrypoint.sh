#!/bin/sh
# Entrypoint para Railway/Render — processo foreground em PID 1.
set -e

cd /app

# Railway injeta PORT; fallback 8080 (não usar --workers: fork quebra detecção Active)
: "${PORT:=8080}"

# Diagnóstico de variáveis antes do uvicorn (Deploy Logs do Railway)
if [ -n "${PIPELINE_API_KEY:-}" ]; then
  echo "PIPELINE_API_KEY presente: True"
else
  echo "PIPELINE_API_KEY presente: False"
fi
if [ -n "${CLOUD_API_KEY:-}" ]; then
  echo "CLOUD_API_KEY presente: True"
else
  echo "CLOUD_API_KEY presente: False"
fi
if [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "GEMINI_API_KEY presente: True"
else
  echo "GEMINI_API_KEY presente: False"
fi
if [ -n "${PEXELS_API_KEY:-}" ]; then
  echo "PEXELS_API_KEY presente: True"
else
  echo "PEXELS_API_KEY presente: False"
fi

if command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg presente: True ($(ffmpeg -version 2>&1 | head -n 1))"
else
  echo "FFmpeg presente: False"
fi

mkdir -p output cache database debug
if touch output/.write_test 2>/dev/null; then
  rm -f output/.write_test
  echo "output/ gravável: True"
else
  echo "output/ gravável: False"
fi

echo "Starting uvicorn on 0.0.0.0:${PORT} (pid $$)"
exec uvicorn api.main_api:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --log-level info \
  --timeout-keep-alive 75
