"""
Override de template de roteiro via variável de ambiente.

Usado pela API Railway (PIPELINE_ROTEIRO_TEMPLATE) para forçar lofi_dark,
dark5, etc., sem monkey-patch no pipeline.
"""

from __future__ import annotations

import os

TEMPLATE_OVERRIDES: dict[str, dict[str, str]] = {
    "lofi_dark": {
        "roteiro_template": "lofi_dark",
        "duracao_alvo": "20 minutos",
    },
    "dark5": {
        "roteiro_template": "dark5",
    },
    "documentario": {
        "roteiro_template": "documentario",
        "duracao_alvo": "8 minutos",
    },
}


def requested_roteiro_template() -> str | None:
    """Template solicitado via env (API/n8n)."""

    value = os.getenv("PIPELINE_ROTEIRO_TEMPLATE", "").strip().lower()
    return value or None


def apply_template_override(strategy: dict) -> dict:
    """
    Aplica override de template na estratégia (inclui resultado de cache).
    """

    template = requested_roteiro_template()
    if not template:
        return strategy

    overrides = TEMPLATE_OVERRIDES.get(template, {"roteiro_template": template})
    merged = dict(strategy)
    merged.update(overrides)
    return merged
