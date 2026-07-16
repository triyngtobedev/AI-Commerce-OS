"""
Soundtrack Engine — trilha sonora emocional com ducking automático.

Gera ou obtém trilha ambiente baseada na Emotional Timeline.
Prioriza Pixabay Music; fallback procedural via FFmpeg.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv

from scripts.core.emotional_effects import get_section_effect_hints
from scripts.core.emotional_timeline import EmotionalTimeline
from scripts.core.production.retry import retry_with_backoff
from scripts.video.media_probe import probe_duration

load_dotenv()

PIXABAY_MUSIC_URL = "https://pixabay.com/api/"

_EMOTION_TO_QUERY: dict[str, str] = {
    "mystery": "dark ambient tension documentary",
    "impact": "epic cinematic dramatic",
    "calm": "soft ambient documentary",
    "warning": "suspense tension rising",
    "sad": "melancholy piano ambient",
    "neutral": "documentary background ambient",
}

_EMOTION_TO_PROCEDURAL: dict[str, dict[str, Any]] = {
    "mystery": {"base_freq": 55, "noise": "brown", "volume": 0.08},
    "impact": {"base_freq": 80, "noise": "pink", "volume": 0.10},
    "calm": {"base_freq": 110, "noise": "pink", "volume": 0.06},
    "warning": {"base_freq": 65, "noise": "brown", "volume": 0.09},
    "sad": {"base_freq": 90, "noise": "pink", "volume": 0.07},
    "neutral": {"base_freq": 100, "noise": "pink", "volume": 0.07},
}


def _dominant_emotion(timeline: EmotionalTimeline | dict | None) -> str:
    if timeline is None:
        return "neutral"

    if isinstance(timeline, dict):
        sections = timeline.get("sections", [])
    else:
        sections = [s.to_dict() for s in timeline.sections]

    if not sections:
        return "neutral"

    scores: dict[str, float] = {}
    for section in sections:
        emotion = section.get("emotion", "neutral")
        intensity = float(section.get("intensity", 0.5))
        duration = float(section.get("real_duration") or section.get("duration") or 10)
        scores[emotion] = scores.get(emotion, 0.0) + duration * intensity

    return max(scores, key=scores.get) if scores else "neutral"


def _search_pixabay_music(query: str, duration: float) -> Optional[str]:
    """Busca música no Pixabay e retorna URL de download."""

    api_key = os.getenv("PIXABAY_API_KEY")
    if not api_key:
        return None

    params = {
        "key": api_key,
        "q": query[:60],
        "per_page": 5,
        "media_type": "music",
    }

    try:
        @retry_with_backoff(max_attempts=2, operation=f"Pixabay music: {query[:30]}")
        def _fetch():
            response = requests.get(PIXABAY_MUSIC_URL, params=params, timeout=15)
            response.raise_for_status()
            return response.json()

        data = _fetch()
        hits = data.get("hits", [])
        for hit in hits:
            duration_hit = hit.get("duration", 0)
            if duration_hit >= min(30, duration * 0.5):
                return hit.get("audio") or hit.get("previewURL")

    except (requests.RequestException, ValueError):
        pass

    return None


def _download_music(url: str, output_path: Path) -> bool:
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                handle.write(chunk)
        return output_path.exists() and output_path.stat().st_size > 1000
    except requests.RequestException:
        return False


def _generate_procedural_soundtrack(
    emotion: str,
    duration: float,
    output_path: Path,
) -> bool:
    """Gera trilha ambiente procedural via FFmpeg lavfi."""

    spec = _EMOTION_TO_PROCEDURAL.get(emotion, _EMOTION_TO_PROCEDURAL["neutral"])
    freq = spec["base_freq"]
    noise = spec["noise"]
    safe_duration = max(30.0, duration + 5.0)

    filter_complex = (
        f"sine=frequency={freq}:sample_rate=44100:duration={safe_duration}[tone];"
        f"anoisesrc=color={noise}:sample_rate=44100:duration={safe_duration},"
        f"lowpass=f=400,volume=0.4[noise];"
        f"[tone][noise]amix=inputs=2:duration=first,volume={spec['volume']},"
        f"afade=t=in:st=0:d=3,afade=t=out:st={safe_duration - 4:.1f}:d=4"
    )

    cmd = [
        "ffmpeg", "-y",
        "-filter_complex", filter_complex,
        "-t", f"{safe_duration:.1f}",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return output_path.exists() and output_path.stat().st_size > 500
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def generate_soundtrack(
    output_path: Path,
    *,
    emotional_timeline: EmotionalTimeline | dict | None = None,
    audio_duration: float = 0.0,
    narration_path: Path | None = None,
) -> Optional[Path]:
    """
    Gera trilha sonora para o vídeo.
    Retorna path do arquivo ou None se falhar.
    """

    if audio_duration <= 0 and narration_path and narration_path.exists():
        audio_duration = probe_duration(narration_path)

    if audio_duration <= 0:
        audio_duration = 300.0

    emotion = _dominant_emotion(emotional_timeline)
    query = _EMOTION_TO_QUERY.get(emotion, _EMOTION_TO_QUERY["neutral"])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    music_url = _search_pixabay_music(query, audio_duration)
    if music_url and _download_music(music_url, output_path):
        print(f"🎵 Trilha Pixabay ({emotion}): {output_path.name}")
        return output_path

    if _generate_procedural_soundtrack(emotion, audio_duration, output_path):
        print(f"🎵 Trilha procedural ({emotion}): {output_path.name}")
        return output_path

    print("⚠️ Trilha sonora não gerada")
    return None


def resolve_soundtrack_hints(timeline: EmotionalTimeline | dict) -> list[dict]:
    """Retorna hints de trilha por seção para relatórios de qualidade."""

    if isinstance(timeline, dict):
        sections = timeline.get("sections", [])
    else:
        sections = [s.to_dict() for s in timeline.sections]

    hints = []
    for section in sections:
        effect = get_section_effect_hints(section)
        hints.append({
            "section": section.get("section_key", ""),
            "emotion": section.get("emotion", "neutral"),
            "soundtrack_hint": effect.get("soundtrack_hint", "neutral_bed"),
        })
    return hints
