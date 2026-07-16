"""
Camada de adaptação Hugging Face -> pipeline existente.

Expõe a mesma assinatura bool-returning do Pollinations. Sem HF_TOKEN,
retorna False silenciosamente para que o pipeline siga no próximo fallback.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from scripts.video.media_providers.huggingface.errors import HFError
from scripts.video.media_providers.huggingface.provider import HuggingFaceProvider

load_dotenv()

logger = logging.getLogger("hf_ai")


def hf_is_configured() -> bool:
    """True se HF_TOKEN está presente."""

    return bool(os.getenv("HF_TOKEN"))


def _reconcile_output_path(asset_path: Path, requested: Path) -> bool:
    requested = Path(requested)
    if asset_path.resolve() == requested.resolve():
        return requested.exists()

    requested.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(asset_path), str(requested))
    return requested.exists()


def generate_hf_image(
    prompt: str,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    timeout: int = 90,
) -> bool:
    """
    Adapter drop-in (mesma assinatura de `generate_pollinations_image`).

    Retorna True se uma imagem válida foi gerada. width/height são ignorados
    na requisição HF (SDXL usa 1024x576); upscale ocorre no visual_media_engine.
    """

    _ = (width, height)
    if not hf_is_configured():
        return False

    try:
        provider = HuggingFaceProvider(request_timeout=timeout)
        asset = provider.generate_image(prompt, output_path=Path(output_path))
        return _reconcile_output_path(asset.path, Path(output_path))
    except HFError as error:
        logger.warning(
            "HF imagem falhou [%s]: %s — fallback para o próximo provedor",
            error.code.value,
            error,
            extra={"model": "-", "kind": "image", "attempt": 0},
        )
        return False
    except Exception as error:
        logger.warning(
            "HF imagem erro inesperado: %s — fallback para o próximo provedor",
            error,
            extra={"model": "-", "kind": "image", "attempt": 0},
        )
        return False
