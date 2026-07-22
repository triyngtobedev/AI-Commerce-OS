# AI-Commerce-OS — Pipeline Python + FFmpeg (Railway / nuvem amd64)
#
# Build:
#   docker build -t ai-commerce-os .
#
# Run local:
#   docker run --env-file .env -p 8000:8000 -v ./output:/app/output ai-commerce-os

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    # Whisper e Hugging Face cache em /tmp (Railway: efêmero mas dentro do ciclo de vida)
    WHISPER_CACHE_DIR=/tmp/whisper_cache \
    HF_HOME=/tmp/huggingface \
    HF_HUB_CACHE=/tmp/huggingface/hub \
    XDG_CACHE_HOME=/tmp/cache

WORKDIR /app

# FFmpeg + dependências de build para faster-whisper / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    libgomp1 \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Cria diretórios de cache no /tmp (garantido existir antes de qualquer processo)
RUN mkdir -p /tmp/whisper_cache /tmp/huggingface/hub /tmp/cache /tmp/output

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Código do projeto
COPY . .

# Diretórios persistentes (montados como volumes em produção)
RUN mkdir -p output cache database debug

# Railway injeta PORT em runtime (não fixar 8000 no EXPOSE)
EXPOSE 8080

RUN chmod +x scripts/cloud/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -sf "http://127.0.0.1:$${PORT:-8080}/api/v1/health" || exit 1

# exec substitui o shell por uvicorn — PID 1 fica vivo (Railway Active, não Completed)
CMD ["/bin/sh", "/app/scripts/cloud/entrypoint.sh"]
