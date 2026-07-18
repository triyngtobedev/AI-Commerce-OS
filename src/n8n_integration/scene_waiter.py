"""
Aguardador assíncrono — polling do resultado de cena via FastAPI job_store.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from src.n8n_integration.config import N8nIntegrationConfig, get_config


async def wait_for_scene(
    scene_id: str,
    job_id: str,
    timeout_seconds: int | None = None,
    config: N8nIntegrationConfig | None = None,
) -> dict[str, Any]:
    """
    Aguarda conclusão da geração de cena via polling na API FastAPI.

    Consulta GET /api/v1/pipeline/status/{job_id} a cada N segundos
    até a cena aparecer com status completed ou failed.

    Args:
        scene_id: Identificador da cena a aguardar.
        job_id: Identificador do job pai.
        timeout_seconds: Timeout máximo (padrão: N8N_SCENE_TIMEOUT ou 300s).
        config: Configuração opcional.

    Returns:
        Dict com video_path, provider_used, status e metadados da cena.

    Raises:
        TimeoutError: Se o timeout for excedido sem resultado.
        RuntimeError: Se a cena falhar no n8n (status failed).
    """
    cfg = config or get_config()
    timeout = timeout_seconds or cfg.scene_default_timeout_seconds
    poll_interval = cfg.scene_poll_interval_seconds
    status_url = cfg.pipeline_status_url_template.format(job_id=job_id)

    headers = {"X-API-Key": cfg.pipeline_api_key}
    elapsed = 0.0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while elapsed < timeout:
            response = await client.get(status_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            scenes = data.get("scenes", {})
            scene_data = scenes.get(scene_id)

            if scene_data:
                status = scene_data.get("status")
                if status == "completed":
                    return {
                        "scene_id": scene_id,
                        "job_id": job_id,
                        "status": status,
                        "video_path": scene_data.get("video_path"),
                        "provider_used": scene_data.get("provider_used"),
                    }
                if status == "failed":
                    raise RuntimeError(
                        scene_data.get("error_message")
                        or f"Scene {scene_id} failed in n8n orchestrator"
                    )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

    raise TimeoutError(
        f"Scene {scene_id} (job {job_id}) not ready after {timeout}s"
    )
