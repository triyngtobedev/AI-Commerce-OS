"""
Configurações da integração n8n — carregadas via python-dotenv.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class N8nIntegrationConfig:
    """Configuração centralizada para comunicação Python ↔ n8n ↔ FastAPI."""

    n8n_scene_webhook_url: str
    n8n_webhook_secret: str
    pipeline_api_base_url: str
    pipeline_callback_base_url: str
    pipeline_api_key: str
    scene_poll_interval_seconds: int = 10
    scene_default_timeout_seconds: int = 300

    @property
    def scene_callback_url(self) -> str:
        """URL do endpoint FastAPI que o n8n chama ao concluir uma cena."""
        base = self.pipeline_callback_base_url.rstrip("/")
        return f"{base}/api/v1/scenes/callback"

    @property
    def pipeline_status_url_template(self) -> str:
        """Template para polling de status: substitua {job_id}."""
        base = self.pipeline_api_base_url.rstrip("/")
        return f"{base}/api/v1/pipeline/status/{{job_id}}"


def get_config() -> N8nIntegrationConfig:
    """
    Carrega configuração a partir de variáveis de ambiente.

    Variáveis obrigatórias:
        N8N_SCENE_WEBHOOK_URL, PIPELINE_API_BASE_URL, PIPELINE_API_KEY
    """
    webhook_url = os.getenv("N8N_SCENE_WEBHOOK_URL", "").strip()
    api_base = os.getenv("PIPELINE_API_BASE_URL", "http://127.0.0.1:8000").strip()
    callback_base = os.getenv("N8N_CALLBACK_BASE_URL", api_base).strip() or api_base
    api_key = os.getenv("PIPELINE_API_KEY", "").strip()

    if not webhook_url:
        raise ValueError("N8N_SCENE_WEBHOOK_URL is not set in environment")
    if not api_key:
        raise ValueError("PIPELINE_API_KEY is not set in environment")

    return N8nIntegrationConfig(
        n8n_scene_webhook_url=webhook_url,
        n8n_webhook_secret=os.getenv("N8N_WEBHOOK_SECRET", "").strip(),
        pipeline_api_base_url=api_base,
        pipeline_callback_base_url=callback_base,
        pipeline_api_key=api_key,
        scene_poll_interval_seconds=int(os.getenv("N8N_SCENE_POLL_INTERVAL", "10")),
        scene_default_timeout_seconds=int(os.getenv("N8N_SCENE_TIMEOUT", "300")),
    )
