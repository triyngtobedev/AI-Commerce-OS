"""
Pollinations Provider — geração gratuita de imagens via IA (sem API key).

Vídeo IA disponível com POLLINATIONS_API_KEY (free tier em enter.pollinations.ai).
"""

from __future__ import annotations

import os
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

POLLINATIONS_IMAGE_BASE = "https://image.pollinations.ai/prompt"
POLLINATIONS_VIDEO_BASE = "https://gen.pollinations.ai/video"


def build_pollinations_url(
    prompt: str,
    width: int = 1920,
    height: int = 1080,
) -> str:
    """Constrói URL de geração de imagem Pollinations."""

    style_prefix = (
        "cinematic documentary photograph, dramatic lighting, "
        "historical atmosphere, photorealistic, 16:9, "
    )
    full_prompt = f"{style_prefix}{prompt}"
    encoded = urllib.parse.quote(full_prompt)

    return (
        f"{POLLINATIONS_IMAGE_BASE}/{encoded}"
        f"?width={width}&height={height}&nologo=true&enhance=true"
    )


def build_pollinations_video_url(
    prompt: str,
    width: int = 1280,
    height: int = 720,
    duration: int = 4,
    model: str = "wan-fast",
) -> str:
    """Constrói URL de geração de vídeo Pollinations."""

    style_prefix = (
        "cinematic documentary footage, smooth camera motion, "
        "historical atmosphere, photorealistic, 16:9, "
    )
    full_prompt = f"{style_prefix}{prompt}"
    encoded = urllib.parse.quote(full_prompt)

    params = (
        f"model={model}&width={width}&height={height}"
        f"&duration={duration}&aspectRatio=16:9&nologo=true"
    )

    api_key = os.getenv("POLLINATIONS_API_KEY")
    if api_key:
        params += f"&key={urllib.parse.quote(api_key)}"

    return f"{POLLINATIONS_VIDEO_BASE}/{encoded}?{params}"


def generate_pollinations_image(
    prompt: str,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
    timeout: int = 90,
) -> bool:
    """
    Gera e salva imagem via Pollinations (gratuito, sem API key).
    """

    url = build_pollinations_url(prompt, width, height)

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        return output_path.exists() and output_path.stat().st_size > 5000

    except Exception as error:
        print(f"⚠️ Pollinations imagem falhou: {error}")
        return False


def generate_pollinations_video(
    prompt: str,
    output_path: Path,
    width: int = 1280,
    height: int = 720,
    duration: int = 4,
    timeout: int = 180,
) -> bool:
    """
    Gera vídeo via Pollinations (requer POLLINATIONS_API_KEY).
    Retorna False silenciosamente se a chave não estiver configurada.
    """

    api_key = os.getenv("POLLINATIONS_API_KEY")
    if not api_key:
        return False

    url = build_pollinations_video_url(prompt, width, height, duration)

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "video" not in content_type and response.content[:4] != b"\x00\x00\x00\x18":
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        if not output_path.exists() or output_path.stat().st_size <= 10000:
            return False

        from scripts.video.media_probe import probe_has_video_stream

        return probe_has_video_stream(output_path)

    except Exception as error:
        print(f"⚠️ Pollinations vídeo falhou: {error}")
        return False
