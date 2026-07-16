"""
Utilitários de duração de mídia via ffprobe.
"""

import json
import subprocess
from pathlib import Path


def probe_duration(path) -> float:
    """
    Retorna duração em segundos de um arquivo de áudio ou vídeo.
    Retorna 0.0 se ffprobe falhar.
    """

    media = Path(path)

    if not media.exists():
        return 0.0

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        str(media.resolve()),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))

    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        return 0.0


def probe_has_video_stream(path) -> bool:
    """Verifica se o arquivo possui stream de vídeo."""

    media = Path(path)

    if not media.exists():
        return False

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-select_streams", "v",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0",
        str(media.resolve()),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return "video" in result.stdout

    except subprocess.CalledProcessError:
        return False
