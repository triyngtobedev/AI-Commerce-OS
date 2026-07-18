"""
Entry point FastAPI — ponte HTTP entre n8n e main.py.

Execução:
    uvicorn api.main_api:app --host 0.0.0.0 --port 8000
    ou: ./api/run_api.sh
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Callable

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from api import __version__
from api.models.schemas import HealthResponse
from api.routers import pipeline, scenes

load_dotenv()

API_KEY = os.getenv("PIPELINE_API_KEY", "")
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
        "/api/v1/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    }

    if path not in public_paths:
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip)

        if not API_KEY:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "PIPELINE_API_KEY not configured"},
            )

        provided_key = request.headers.get("X-API-Key", "")
        if provided_key != API_KEY:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing X-API-Key header"},
            )

    return await call_next(request)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Health check simples — usado por n8n e monitoramento."""
    return HealthResponse(status="ok", version=__version__)


# Registra routers sob prefixo /api/v1
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(scenes.router, prefix="/api/v1")
