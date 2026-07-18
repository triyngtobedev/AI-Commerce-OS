"""
Cliente HTTP — envia pedidos de geração de cena ao webhook n8n.
"""

from __future__ import annotations

from typing import Any

import httpx

from src.n8n_integration.config import N8nIntegrationConfig, get_config


async def request_scene_generation(
    scene_prompt: str,
    scene_id: str,
    job_id: str,
    metadata: dict[str, Any] | None = None,
    config: N8nIntegrationConfig | None = None,
) -> dict[str, Any]:
    """
    Envia pedido de geração de cena ao workflow n8n via webhook.

    Args:
        scene_prompt: Prompt descritivo para geração do vídeo da cena.
        scene_id: Identificador único da cena dentro do job.
        job_id: Identificador do job de pipeline pai.
        metadata: Metadados extras (duração, aspect ratio, estilo, etc.).
        config: Configuração opcional (padrão: carrega do .env).

    Returns:
        Resposta JSON de acknowledgment do n8n.

    Raises:
        httpx.HTTPStatusError: Se o n8n retornar erro HTTP.
    """
    cfg = config or get_config()
    payload = {
        "scene_id": scene_id,
        "job_id": job_id,
        "prompt": scene_prompt,
        "metadata": metadata or {},
        "callback_url": cfg.scene_callback_url,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if cfg.n8n_webhook_secret:
        headers["X-Webhook-Secret"] = cfg.n8n_webhook_secret

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            cfg.n8n_scene_webhook_url,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

        # n8n pode retornar JSON ou texto simples
        try:
            return response.json()
        except ValueError:
            return {"status": "accepted", "raw_response": response.text}
