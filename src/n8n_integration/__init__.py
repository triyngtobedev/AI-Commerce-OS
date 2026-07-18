"""
Integração assíncrona com n8n — geração de cenas de vídeo via webhook.

Este módulo é isolado do core do pipeline; não altera scripts/ existentes.
"""

from src.n8n_integration.config import N8nIntegrationConfig, get_config
from src.n8n_integration.scene_client import request_scene_generation
from src.n8n_integration.scene_waiter import wait_for_scene

__all__ = [
    "N8nIntegrationConfig",
    "get_config",
    "request_scene_generation",
    "wait_for_scene",
]
