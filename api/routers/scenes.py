"""
Rotas de callback de cenas — recebe resultados assíncronos do n8n.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from api.models.schemas import SceneCallbackRequest, SceneCallbackResponse, SceneStatus
from api.services.job_store import job_store

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.post("/callback", response_model=SceneCallbackResponse)
async def scene_callback(payload: SceneCallbackRequest) -> SceneCallbackResponse:
    """
    Endpoint chamado pelo n8n quando uma cena de vídeo fica pronta ou falha.

    Atualiza job_store e dispara asyncio.Event para waiters in-process.
    """
    job = job_store.get_job(payload.job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {payload.job_id} not found",
        )

    job_store.update_scene(
        job_id=payload.job_id,
        scene_id=payload.scene_id,
        status=payload.status,
        video_path=payload.video_path,
        provider_used=payload.provider_used,
        error_message=payload.error_message,
    )

    return SceneCallbackResponse(
        accepted=True,
        scene_id=payload.scene_id,
        job_id=payload.job_id,
        message=(
            "Scene completed"
            if payload.status == SceneStatus.COMPLETED
            else "Scene callback processed"
        ),
    )
