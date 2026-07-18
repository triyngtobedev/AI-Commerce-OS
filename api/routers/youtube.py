"""
Rotas YouTube — upload acionado pelo n8n após job concluído.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.services.youtube_service import upload_job_video, upload_output_folder

router = APIRouter(prefix="/youtube", tags=["youtube"])


class YouTubeUploadRequest(BaseModel):
    """Upload de vídeo após pipeline concluído."""

    job_id: UUID | None = Field(
        default=None,
        description="ID do job concluído no Railway",
    )
    output_folder: str | None = Field(
        default=None,
        description="Pasta de output alternativa (sem job_id)",
    )
    force: bool = Field(
        default=False,
        description="Força upload mesmo sem YOUTUBE_AUTO_UPLOAD",
    )


class YouTubeUploadResponse(BaseModel):
    success: bool
    status: str | None = None
    video_id: str | None = None
    url: str | None = None
    message: str = ""
    skipped: bool = False


@router.post("/upload", response_model=YouTubeUploadResponse, status_code=status.HTTP_200_OK)
async def upload_video(request: YouTubeUploadRequest) -> YouTubeUploadResponse:
    """
    Faz upload do vídeo final para o YouTube.

    Acionado pelo n8n após job completed ou manualmente via API.
    Requer credenciais OAuth configuradas no Railway.
    """
    if request.job_id:
        result = await upload_job_video(request.job_id, force=request.force)
    elif request.output_folder:
        result = upload_output_folder(Path(request.output_folder))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe job_id ou output_folder",
        )

    if not result.get("success") and not result.get("skipped"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.get("message", "Upload falhou"),
        )

    return YouTubeUploadResponse(
        success=result.get("success", False),
        status=result.get("status"),
        video_id=result.get("video_id"),
        url=result.get("url"),
        message=result.get("message", ""),
        skipped=result.get("skipped", False),
    )