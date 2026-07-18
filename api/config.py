"""
Configuração compartilhada da API FastAPI (variáveis de ambiente).
"""

from __future__ import annotations

import os


def get_pipeline_api_key() -> str:
    """
    Chave de autenticação da API (header X-API-Key).

    Railway/produção: defina PIPELINE_API_KEY.
    PC local (cliente): usa CLOUD_API_KEY com o mesmo valor.
    Aceita CLOUD_API_KEY como fallback para evitar 503 quando só esse nome
    foi configurado no painel.
    """
    return (
        os.getenv("PIPELINE_API_KEY", "").strip()
        or os.getenv("CLOUD_API_KEY", "").strip()
    )
