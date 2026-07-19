"""
Rotas de pipeline — acionamento, status e download via HTTP.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from api.models.schemas import (
    JobStatus,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
)
from api.services.job_store import job_store
from api.services.pipeline_runner import PROJECT_ROOT, run_pipeline_subprocess

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
        "template": request.template,
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
        # Jobs são sempre UUID; identificador inválido = recurso inexistente (404).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        ) from exc

    job = job_store.get_job(parsed_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return PipelineStatusResponse(**job)


@router.get("/download/{job_id}")
async def download_pipeline_output(job_id: str) -> FileResponse:
    """
    Baixa o vídeo final de um job concluído.

    Usado pelo script local scripts/cloud/gerar_video.py.
    """
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

    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job ainda não concluído (status: {job['status'].value})",
        )

    raw_path = job.get("output_path")
    if not raw_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job concluído mas sem caminho de saída registrado",
        )

    video_path = Path(raw_path)
    if not video_path.is_absolute():
        video_path = PROJECT_ROOT / video_path

    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo não encontrado: {video_path.name}",
        )

    # Restringe download a arquivos dentro do projeto (output/)
    try:
        video_path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caminho de saída fora do diretório permitido",
        ) from exc

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name,
    )
