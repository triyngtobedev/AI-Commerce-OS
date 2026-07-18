"""
Rotas de pipeline — acionamento e consulta de status via HTTP.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from api.models.schemas import (
    JobStatus,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
)
from api.services.job_store import job_store
from api.services.pipeline_runner import run_pipeline_subprocess

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    """
    Enfileira execução do pipeline Python (main.py) como subprocess assíncrono.

    Retorna imediatamente job_id para polling via GET /pipeline/status/{job_id}.
    """
    job_id = uuid4()
    metadata = {
        **request.metadata,
        "topic": request.topic,
        "language": request.language,
        "platform": request.platform,
    }
    job_store.create_job(job_id, metadata=metadata)

    # Dispara subprocess em background sem bloquear a resposta HTTP
    asyncio.create_task(run_pipeline_subprocess(job_id, request))

    return PipelineRunResponse(job_id=job_id, status=JobStatus.QUEUED)


@router.get("/status/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(job_id: str) -> PipelineStatusResponse:
    """
    Retorna status atual do job, incluindo resultados de cenas (scenes).

    Usado pelo n8n (polling) e pelo scene_waiter do módulo n8n_integration.
    """
    from uuid import UUID

    try:
        parsed_id = UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job_id format",
        ) from exc

    job = job_store.get_job(parsed_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return PipelineStatusResponse(**job)
