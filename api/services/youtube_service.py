"""
Serviço de upload YouTube acionado via API (n8n / Railway).
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from api.models.schemas import JobStatus
from api.services.job_store import job_store
from scripts.analytics.video_registry import get_all_videos
from scripts.publisher.youtube_publish_config import resolve_upload_settings, resolve_upload_visibility
from scripts.publisher.youtube_uploader import UPLOAD_STATUS
from scripts.youtube.uploader import upload_from_job_output


def should_auto_upload() -> bool:
    """Verifica se YOUTUBE_AUTO_UPLOAD está habilitado no Railway."""
    should_upload, _ = resolve_upload_settings(cli_upload=False)
    return should_upload


async def upload_job_video(job_id: UUID, *, force: bool = False) -> dict:
    """
    Faz upload do vídeo de um job concluído.

    Args:
        job_id: UUID do job no job_store
        force: Ignora YOUTUBE_AUTO_UPLOAD e força upload

    Returns:
        Resultado do upload ou erro descritivo
    """
    job = job_store.get_job(job_id)
    if job is None:
        return {"success": False, "message": f"Job {job_id} não encontrado"}

    if job["status"] != JobStatus.COMPLETED:
        return {
            "success": False,
            "message": f"Job ainda não concluído (status: {job['status'].value})",
        }

    # Idempotência — evita re-upload se job já foi publicado
    job_id_str = str(job_id)
    for video in get_all_videos():
        if video.get("job_id") == job_id_str and video.get("video_url"):
            return {
                "success": True,
                "status": UPLOAD_STATUS["uploaded"],
                "video_id": video.get("video_id"),
                "url": video.get("video_url"),
                "message": "Vídeo já publicado para este job",
            }

    output_path = job.get("output_path")
    if not output_path:
        return {"success": False, "message": "Job concluído sem output_path"}

    if not force and not should_auto_upload():
        return {
            "success": False,
            "skipped": True,
            "message": "YOUTUBE_AUTO_UPLOAD não está habilitado. Use force=true ou defina YOUTUBE_AUTO_UPLOAD=true",
        }

    privacy_status, _ = resolve_upload_visibility()
    result = upload_from_job_output(
        output_path,
        privacy_status=privacy_status,
        job_id=str(job_id),
    )

    success = result.get("status") == UPLOAD_STATUS["uploaded"]
    return {
        "success": success,
        "status": result.get("status"),
        "video_id": result.get("video_id"),
        "url": result.get("url"),
        "message": result.get("message", ""),
        "registry": result.get("registry"),
    }


def upload_output_folder(folder: Path | str, *, job_id: str | None = None) -> dict:
    """Upload direto a partir de uma pasta de output."""
    from scripts.youtube.uploader import upload_video_folder

    privacy_status, _ = resolve_upload_visibility()
    result = upload_video_folder(folder, privacy_status=privacy_status, job_id=job_id)
    success = result.get("status") == UPLOAD_STATUS["uploaded"]
    return {
        "success": success,
        "status": result.get("status"),
        "video_id": result.get("video_id"),
        "url": result.get("url"),
        "message": result.get("message", ""),
        "registry": result.get("registry"),
    }
