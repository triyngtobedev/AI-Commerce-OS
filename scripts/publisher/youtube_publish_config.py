"""
Configuração de publicação YouTube.

Centraliza flags que controlam upload automático e visibilidade.
"""

import os
from typing import Dict, Optional, Tuple

VALID_VISIBILITY = ("private", "unlisted", "public")


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


def resolve_upload_visibility(
    cli_privacy: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    """
    Resolve visibilidade do upload YouTube.

    Prioridade:
        1. --privacy (CLI), quando informado
        2. UPLOAD_VISIBILITY no .env
        3. private (padrão seguro)

    O pipeline nunca deve hardcodar visibilidade — sempre usar esta função.
    """

    env_value = os.getenv("UPLOAD_VISIBILITY", "unlisted").strip().lower()
    context = {
        "upload_visibility_env": os.getenv("UPLOAD_VISIBILITY", ""),
        "cli_privacy": cli_privacy or "",
    }

    if cli_privacy:
        value = cli_privacy.strip().lower()
        if value not in VALID_VISIBILITY:
            value = "private"
        context["decision"] = value
        context["reason"] = "Flag --privacy informada"
        return value, context

    if env_value in VALID_VISIBILITY:
        context["decision"] = env_value
        context["reason"] = f"UPLOAD_VISIBILITY={env_value} no .env"
        return env_value, context

    context["decision"] = "unlisted"
    context["reason"] = (
        f"UPLOAD_VISIBILITY inválido ({env_value!r}) — "
        "usando unlisted (não listado) como padrão seguro"
    )
    return "unlisted", context
