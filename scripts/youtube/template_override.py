"""
Override de roteiro_template via env (API / nuvem / CLI).

PIPELINE_ROTEIRO_TEMPLATE força o template independente da estratégia gerada pela IA.
"""

from __future__ import annotations

import os

from scripts.youtube.lofi_dark_config import is_lofi_dark

ENV_ROTEIRO_TEMPLATE = "PIPELINE_ROTEIRO_TEMPLATE"


def get_template_override() -> str | None:
    """Retorna template forçado via env, ou None se ausente."""
    value = os.getenv(ENV_ROTEIRO_TEMPLATE, "").strip()
    return value or None


def apply_template_override(strategy: dict) -> dict:
    """Aplica PIPELINE_ROTEIRO_TEMPLATE à estratégia, se definido."""
    template = get_template_override()
    if not template:
        return strategy

    strategy["roteiro_template"] = template
    if is_lofi_dark(template):
        strategy["duracao_alvo"] = "20 minutos"
    return strategy
