"""
Download de vídeos gerados — rota pública para revisão no browser.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from api.services.output_videos import get_latest_video_final, is_allowed_output_path

router = APIRouter(tags=["download"])


@router.get("/download/latest-video")
async def download_latest_video() -> FileResponse:
    """
    Baixa o video_final.mp4 mais recente encontrado em output/.

    Rota pública (sem X-API-Key) para revisão de qualidade via browser.
    """
    video_path = get_latest_video_final()
    if video_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum video_final.mp4 encontrado em output/",
        )

    try:
        if not is_allowed_output_path(video_path):
            raise ValueError("outside allowed output directories")
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
