"""
Schemas Pydantic — validação de payloads da API de integração n8n.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Estados possíveis de um job de pipeline ou cena."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


class SceneStatus(str, Enum):
    """Estados de geração de uma cena individual."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineRunRequest(BaseModel):
    """
    Parâmetros para acionar o pipeline via HTTP.

    Mapeia diretamente para os argumentos CLI suportados por main.py.
    Campos extras (topic, language) são preservados em metadata para uso futuro.
    """

    platform: str = Field(
        default="youtube_dark",
        description="Plataforma alvo: tiktok_shop | youtube_dark | all",
    )
    production: bool = Field(
        default=False,
        description="Modo produção completo (--production)",
    )
    research: bool = Field(
        default=False,
        description="Pesquisa automática de temas (--research)",
    )
    upload: bool = Field(
        default=False,
        description="Upload automático no YouTube (--upload)",
    )
    privacy: Optional[str] = Field(
        default=None,
        description="Visibilidade do upload: private | unlisted | public",
    )
    max_videos: Optional[int] = Field(
        default=1,
        ge=1,
        description="Número máximo de vídeos a produzir",
    )
    force: bool = Field(
        default=False,
        description="Reprocessar temas já gerados (--force)",
    )
    topic: str | None = Field(
        default=None,
        description="Tema específico injetado pelo n8n. "
                    "Se ausente, pipeline usa fonte de temas padrão.",
        example="crimes famosos não resolvidos",
    )
    template: str | None = Field(
        default=None,
        description="Template de roteiro forçado: documentario | dark5 | lofi_dark",
        example="lofi_dark",
    )
    language: Optional[str] = Field(
        default="pt-BR",
        description="Idioma do conteúdo (metadata para workflows n8n)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados adicionais repassados ao job",
    )


class PipelineRunResponse(BaseModel):
    """Resposta imediata ao enfileirar um job de pipeline."""

    job_id: UUID
    status: JobStatus = JobStatus.QUEUED
    message: str = "Pipeline job enqueued"


class SceneResult(BaseModel):
    """Resultado de geração de uma cena individual."""

    scene_id: str
    status: SceneStatus = SceneStatus.PENDING
    video_path: Optional[str] = None
    provider_used: Optional[str] = None
    error_message: Optional[str] = None
    updated_at: Optional[datetime] = None


class PipelineStatusResponse(BaseModel):
    """Status detalhado de um job de pipeline."""

    job_id: UUID
    status: JobStatus
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    stdout_tail: Optional[str] = Field(
        default=None,
        description="Últimas linhas do stdout do subprocess (diagnóstico, inclui AI Router)",
    )
    scenes: dict[str, SceneResult] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneCallbackRequest(BaseModel):
    """Payload enviado pelo n8n quando uma cena fica pronta (ou falha)."""

    scene_id: str
    job_id: UUID
    video_path: Optional[str] = None
    provider_used: Optional[str] = None
    status: SceneStatus
    error_message: Optional[str] = None


class SceneCallbackResponse(BaseModel):
    """Confirmação de recebimento do callback de cena."""

    accepted: bool = True
    scene_id: str
    job_id: UUID
    message: str = "Scene callback processed"


class HealthResponse(BaseModel):
    """Resposta do health check."""

    status: str = "ok"
    version: str
    service: str = "ai-commerce-os-pipeline-api"
    auth_configured: bool = False
    git_commit: str | None = None
    persistent_storage: bool = False
