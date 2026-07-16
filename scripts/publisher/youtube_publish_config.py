"""
Configuração de publicação YouTube.

Centraliza flags que controlam upload automático.
"""

import os
from typing import Dict, Tuple


def _env_flag(name: str, default: str = "false") -> bool:
    """Interpreta variável de ambiente como booleano."""

    return os.getenv(name, default).strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def resolve_upload_settings(
    cli_upload: bool = False,
) -> Tuple[bool, Dict[str, str]]:
    """
    Resolve se o upload automático deve ocorrer.

    Prioridade:
        1. YOUTUBE_DRY_RUN=true  → bloqueia upload
        2. --upload (CLI)         → força upload
        3. YOUTUBE_AUTO_UPLOAD    → habilita upload via .env

    Returns:
        (should_upload, contexto com motivo da decisão)
    """

    dry_run = _env_flag("YOUTUBE_DRY_RUN")
    env_auto_upload = _env_flag("YOUTUBE_AUTO_UPLOAD")
    publish_enabled = _env_flag("YOUTUBE_PUBLISH_ENABLED", "true")

    context = {
        "cli_upload": str(cli_upload),
        "youtube_auto_upload": os.getenv(
            "YOUTUBE_AUTO_UPLOAD",
            "false",
        ),
        "youtube_dry_run": os.getenv(
            "YOUTUBE_DRY_RUN",
            "false",
        ),
        "youtube_publish_enabled": os.getenv(
            "YOUTUBE_PUBLISH_ENABLED",
            "true",
        ),
    }

    if dry_run:
        context["decision"] = "blocked"
        context["reason"] = (
            "YOUTUBE_DRY_RUN=true — upload desabilitado"
        )
        return False, context

    if not publish_enabled:
        context["decision"] = "blocked"
        context["reason"] = (
            "YOUTUBE_PUBLISH_ENABLED=false — "
            "publicação desabilitada"
        )
        return False, context

    if cli_upload:
        context["decision"] = "enabled"
        context["reason"] = "Flag --upload informada"
        return True, context

    if env_auto_upload:
        context["decision"] = "enabled"
        context["reason"] = (
            "YOUTUBE_AUTO_UPLOAD=true no .env"
        )
        return True, context

    context["decision"] = "disabled"
    context["reason"] = (
        "Upload não solicitado. Use --upload ou "
        "defina YOUTUBE_AUTO_UPLOAD=true no .env"
    )

    return False, context
