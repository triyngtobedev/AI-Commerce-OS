#!/bin/sh
# Entrypoint para Railway/Render — processo foreground em PID 1.
set -euo pipefail

cd /app

: "${PORT:=8080}"

echo "=== ai-commerce-os startup ==="
echo "Commit: ${RAILWAY_GIT_COMMIT_SHA:-${GIT_COMMIT:-desconhecido}}"
echo "Data:   $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Python: $(python --version 2>&1 || echo 'indisponível')"

# ── Caches temporários (Railway: filesystem efêmero, persiste no ciclo de vida) ──
export WHISPER_CACHE_DIR="${WHISPER_CACHE_DIR:-/tmp/whisper_cache}"
export HF_HOME="${HF_HOME:-/tmp/huggingface}"
export HF_HUB_CACHE="${HF_HUB_CACHE:-/tmp/huggingface/hub}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/cache}"

mkdir -p "$WHISPER_CACHE_DIR" "$HF_HOME" "$HF_HUB_CACHE" "$XDG_CACHE_HOME"

# ── Volume persistente (Railway Volume mount) ──
PERSISTENT_BASE="${PERSISTENT_DIR:-/app/persistent}"

if [ -d "$PERSISTENT_BASE" ]; then
  echo "Volume persistente detectado em $PERSISTENT_BASE"
  mkdir -p "$PERSISTENT_BASE/database" "$PERSISTENT_BASE/output" "$PERSISTENT_BASE/reports"
  export DATABASE_PATH="${DATABASE_PATH:-$PERSISTENT_BASE/database/pipeline_jobs.db}"
  export OUTPUT_DIR="${OUTPUT_DIR:-$PERSISTENT_BASE/output}"
  export REPORTS_DIR="${REPORTS_DIR:-$PERSISTENT_BASE/reports}"
else
  echo "Sem volume persistente — dados serão perdidos em restart."
  echo "Configure um volume em /app/persistent no Railway (docs/railway-volume.md)."
  mkdir -p /app/database /app/output /app/reports /app/logs /app/cache /app/debug
  export OUTPUT_DIR="${OUTPUT_DIR:-/app/output}"
fi

# Garante que o diretório de output existe e é gravável
mkdir -p "$OUTPUT_DIR"

echo ""
echo "=== Configuração ==="

check_var() {
  if [ -n "${!1:-}" ]; then
    echo "  ✓ $1 configurada"
  else
    echo "  ! $1 NÃO configurada"
  fi
}

check_var "PIPELINE_API_KEY"
check_var "CLOUD_API_KEY"
check_var "GEMINI_API_KEY"
check_var "GROQ_API_KEY"
check_var "OPENROUTER_API_KEY"
check_var "PEXELS_API_KEY"
check_var "YOUTUBE_AUTO_UPLOAD"
check_var "DATABASE_PATH"

if command -v ffmpeg >/dev/null 2>&1; then
  echo "  ✓ FFmpeg presente ($(ffmpeg -version 2>&1 | head -n 1))"
else
  echo "  ! FFmpeg ausente"
fi

OUTPUT_TEST="${OUTPUT_DIR:-/app/output}"
mkdir -p "$OUTPUT_TEST"
if touch "$OUTPUT_TEST/.write_test" 2>/dev/null; then
  rm -f "$OUTPUT_TEST/.write_test"
  echo "  ✓ output gravável: $OUTPUT_TEST"
else
  echo "  ! output não gravável: $OUTPUT_TEST"
fi

echo ""
echo "=== Iniciando API ==="
echo "Porta: ${PORT}"

exec uvicorn api.main_api:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --log-level info \
  --timeout-keep-alive 75
