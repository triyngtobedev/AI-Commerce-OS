"""
Entry point FastAPI — ponte HTTP entre n8n e main.py.

Execução:
    uvicorn api.main_api:app --host 0.0.0.0 --port 8000
    ou: ./api/run_api.sh
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from typing import Callable

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse

from api import __version__
from api.config import get_pipeline_api_key
from api.models.schemas import HealthResponse
from api.routers import analytics, pipeline, scenes, test_images, youtube
from api.services.output_videos import get_latest_video_final, is_allowed_output_path

load_dotenv()

logger = logging.getLogger("uvicorn.error")
RATE_LIMIT_REQUESTS = int(os.getenv("PIPELINE_API_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("PIPELINE_API_RATE_WINDOW", "60"))

app = FastAPI(
    title="AI-Commerce-OS Pipeline API",
    description="Bridge HTTP entre n8n e o pipeline Python (main.py)",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# --- Rate limiting in-memory (por IP) ---
_request_log: dict[str, deque[float]] = defaultdict(deque)


def _check_rate_limit(client_ip: str) -> None:
    """Limita requisições por IP dentro da janela configurada."""
    now = time.monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    log = _request_log[client_ip]

    while log and log[0] < window_start:
        log.popleft()

    if len(log) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    log.append(now)


@app.middleware("http")
async def security_middleware(request: Request, call_next: Callable):
    """
    Middleware de autenticação (X-API-Key) e rate limiting.

    Rotas públicas: /api/v1/health e documentação OpenAPI.
    """
    path = request.url.path
    public_paths = {
        "/health",
        "/api/v1/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/download/latest-video",
    }

    if path not in public_paths:
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip)

        api_key = get_pipeline_api_key()
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": (
                        "PIPELINE_API_KEY not configured "
                        "(defina PIPELINE_API_KEY ou CLOUD_API_KEY no Railway)"
                    )
                },
            )

        provided_key = request.headers.get("X-API-Key", "").strip()
        if provided_key != api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing X-API-Key header"},
            )

    return await call_next(request)


@app.on_event("startup")
async def log_auth_config() -> None:
    """Avisa no log do Railway se a chave de API não estiver configurada."""
    git_commit = os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown")
    print(f"GIT_COMMIT: {git_commit}", flush=True)

    # Diagnóstico explícito nos logs do Railway (stdout, visível no Deploy Logs)
    print(
        f"PIPELINE_API_KEY presente: {bool(os.getenv('PIPELINE_API_KEY'))}",
        flush=True,
    )
    print(
        f"CLOUD_API_KEY presente: {bool(os.getenv('CLOUD_API_KEY'))}",
        flush=True,
    )
    print(
        f"auth_configured (get_pipeline_api_key): {bool(get_pipeline_api_key())}",
        flush=True,
    )
    print(
        f"GEMINI_API_KEY presente: {bool(os.getenv('GEMINI_API_KEY'))}",
        flush=True,
    )
    print(
        f"GROQ_API_KEY presente: {bool(os.getenv('GROQ_API_KEY'))}",
        flush=True,
    )
    print(
        f"OPENROUTER_API_KEY presente: {bool(os.getenv('OPENROUTER_API_KEY'))}",
        flush=True,
    )
    print(
        f"PEXELS_API_KEY presente: {bool(os.getenv('PEXELS_API_KEY'))}",
        flush=True,
    )

    if get_pipeline_api_key():
        if not os.getenv("PIPELINE_API_KEY", "").strip() and os.getenv(
            "CLOUD_API_KEY", ""
        ).strip():
            logger.warning(
                "CLOUD_API_KEY detectada sem PIPELINE_API_KEY — "
                "funciona, mas prefira PIPELINE_API_KEY no Railway"
            )
    else:
        logger.warning(
            "PIPELINE_API_KEY/CLOUD_API_KEY ausente — "
            "POST /api/v1/pipeline/run retornará 503 até configurar no Railway"
        )

    if not os.getenv("GEMINI_API_KEY", "").strip():
        logger.warning(
            "GEMINI_API_KEY ausente — pipeline usará Groq como fallback (qualidade reduzida)"
        )


@app.get("/health", response_model=HealthResponse, tags=["health"])
@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check simples — usado por Railway, n8n e monitoramento."""
    persistent_dir = os.getenv("PERSISTENT_DIR", "/app/persistent")
    git_commit = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GIT_COMMIT")
        or None
    )
    return HealthResponse(
        status="ok",
        version=__version__,
        auth_configured=bool(get_pipeline_api_key()),
        git_commit=git_commit,
        persistent_storage=os.path.isdir(persistent_dir),
    )


@app.get("/download/latest-video", tags=["download"])
@app.head("/download/latest-video", tags=["download"])
def download_latest_video() -> FileResponse:
    """Baixa o video_final.mp4 mais recente em /app/persistent/output ou /app/output."""
    video_path = get_latest_video_final()
    if video_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum video_final.mp4 encontrado em output/",
        )

    if not is_allowed_output_path(video_path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caminho de saída fora do diretório permitido",
        )

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename="video.mp4",
    )


# Registra routers sob prefixo /api/v1
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(scenes.router, prefix="/api/v1")
app.include_router(youtube.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(test_images.router, prefix="/api/v1")
