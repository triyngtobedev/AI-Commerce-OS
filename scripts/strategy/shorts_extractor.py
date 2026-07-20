"""
Extrator de YouTube Shorts a partir do vídeo principal.

Seleciona a cena de maior peso emocional (scene_weight na timeline) e
gera short_final.mp4 em 9:16 com legendas recortadas.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

from scripts.video.media_probe import probe_duration, probe_video_bitrate
from scripts.video.scene_timeline import extract_scenes, _scene_weight
from scripts.video.subtitle_engine import ffmpeg_subtitle_filter

MAX_SHORT_DURATION = 60.0
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

_ASS_DIALOGUE = re.compile(
    r"^Dialogue:\s*\d+,([^,]+),([^,]+),",
    re.MULTILINE,
)


def _is_enabled() -> bool:
    return os.getenv("USE_SHORTS_EXTRACTOR", "false").lower() in ("true", "1", "yes")


def _scene_emotional_weight(scene: dict) -> float:
    """
    Peso emocional da cena.

    Campo canônico: timeline.scene_weight (Emotional Timeline).
    Fallback: peso por tipo de cena (SCENE_WEIGHTS).
    Desempate: intensity (0–1).
    """

    timeline = scene.get("timeline") or {}
    weight = timeline.get("scene_weight")
    if weight is None:
        weight = _scene_weight(scene)
    intensity = float(scene.get("intensity", timeline.get("intensity", 0.0)) or 0.0)
    return float(weight) + intensity * 0.01


def _scene_name(scene: dict) -> str:
    timeline = scene.get("timeline") or {}
    return str(
        scene.get("tipo")
        or timeline.get("section_key")
        or scene.get("narracao", "")[:40]
        or "cena"
    )


def _scene_time_bounds(scene: dict) -> tuple[float, float]:
    inicio = scene.get("tempo_inicio")
    fim = scene.get("tempo_fim")
    if inicio is not None and fim is not None:
        return float(inicio), float(fim)

    tempo = scene.get("tempo", "0-5")
    try:
        start, end = tempo.split("-", 1)
        return float(start), float(end)
    except ValueError:
        duration = float(scene.get("duration_seconds") or 5.0)
        return 0.0, duration


def _select_best_scene(scenes: list[dict]) -> dict:
    if not scenes:
        raise ValueError("Nenhuma cena disponível em script_data")

    return max(scenes, key=_scene_emotional_weight)


def _parse_ass_time(value: str) -> float:
    """Converte timestamp ASS (H:MM:SS.cc) para segundos."""

    parts = value.strip().split(":")
    if len(parts) != 3:
        return 0.0
    hours = int(parts[0])
    minutes = int(parts[1])
    sec_parts = parts[2].split(".")
    seconds = int(sec_parts[0])
    centis = int(sec_parts[1]) if len(sec_parts) > 1 else 0
    return hours * 3600 + minutes * 60 + seconds + centis / 100.0


def _format_ass_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds % 1) * 100))
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _clip_ass_content(
    ass_content: str,
    clip_start: float,
    clip_end: float,
    *,
    play_res_x: int = SHORT_WIDTH,
    play_res_y: int = SHORT_HEIGHT,
) -> str:
    """Recorta eventos ASS para o intervalo e rebaseia timestamps em 00:00."""

    lines = ass_content.splitlines()
    output: list[str] = []
    in_events = False

    for line in lines:
        if line.startswith("PlayResX:"):
            output.append(f"PlayResX: {play_res_x}")
            continue
        if line.startswith("PlayResY:"):
            output.append(f"PlayResY: {play_res_y}")
            continue

        if line.strip() == "[Events]":
            in_events = True
            output.append(line)
            continue

        if not line.startswith("Dialogue:"):
            output.append(line)
            continue

        match = _ASS_DIALOGUE.match(line)
        if not match:
            output.append(line)
            continue

        start_t = _parse_ass_time(match.group(1))
        end_t = _parse_ass_time(match.group(2))

        if end_t <= clip_start or start_t >= clip_end:
            continue

        new_start = max(0.0, start_t - clip_start)
        new_end = min(clip_end - clip_start, end_t - clip_start)
        if new_end <= new_start:
            continue

        prefix = line[: match.start(1)]
        suffix = line[match.end(2) :]
        rebuilt = (
            f"{prefix}{_format_ass_time(new_start)},"
            f"{_format_ass_time(new_end)}{suffix}"
        )
        output.append(rebuilt)

    if not in_events:
        return ass_content

    return "\n".join(output) + "\n"


def _build_vertical_filter(ass_path: Optional[Path]) -> str:
    """
    16:9 → 9:16: crop centralizado na maior área 9:16, escala para 1080x1920
    e padding preto nas laterais se necessário.
    """

    base = (
        f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
        f"scale={SHORT_WIDTH}:{SHORT_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={SHORT_WIDTH}:{SHORT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
    )
    if ass_path and ass_path.exists():
        ass_filter = ffmpeg_subtitle_filter(ass_path)
        return f"{base},{ass_filter}"
    return base


def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(f"FFmpeg falhou: {stderr[-800:]}")


def extract_short(job_output_dir: Path | str, script_data: Any) -> dict:
    """
    Gera short_final.mp4 a partir do vídeo principal.

    Args:
        job_output_dir: Pasta do job (contém video_final.mp4 e captions.ass).
        script_data: Payload de cenas (dict com chave ``cenas``) ou resultado
            completo do pipeline (``result["cenas"]``).

    Returns:
        dict com ``path``, ``duration`` e ``scene_name``.
    """

    output_dir = Path(job_output_dir)
    video_path = output_dir / "video_final.mp4"
    ass_path = output_dir / "captions.ass"
    short_path = output_dir / "short_final.mp4"

    if not video_path.is_file():
        raise FileNotFoundError(f"video_final.mp4 não encontrado em {output_dir}")

    scenes = extract_scenes(script_data)
    if not scenes and isinstance(script_data, dict):
        scenes = extract_scenes(script_data.get("cenas", script_data))

    best_scene = _select_best_scene(scenes)
    scene_start, scene_end = _scene_time_bounds(best_scene)
    clip_duration = min(scene_end - scene_start, MAX_SHORT_DURATION)
    if clip_duration <= 0:
        clip_duration = min(
            float(best_scene.get("duration_seconds") or MAX_SHORT_DURATION),
            MAX_SHORT_DURATION,
        )
        scene_end = scene_start + clip_duration

    clip_end = scene_start + clip_duration
    scene_name = _scene_name(best_scene)

    clipped_ass: Optional[Path] = None
    if ass_path.is_file():
        ass_text = ass_path.read_text(encoding="utf-8")
        clipped_text = _clip_ass_content(ass_text, scene_start, clip_end)
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ass",
            delete=False,
            encoding="utf-8",
        )
        tmp.write(clipped_text)
        tmp.close()
        clipped_ass = Path(tmp.name)

    video_filter = _build_vertical_filter(clipped_ass)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(scene_start),
        "-t",
        str(clip_duration),
        "-i",
        str(video_path.resolve()),
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
    ]

    bitrate = probe_video_bitrate(video_path)
    if bitrate and bitrate > 0:
        cmd.extend(["-b:v", str(bitrate)])
    else:
        cmd.extend(["-crf", "21"])

    cmd.extend([
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(short_path.resolve()),
    ])

    try:
        _run_ffmpeg(cmd)
    finally:
        if clipped_ass and clipped_ass.exists():
            clipped_ass.unlink(missing_ok=True)

    actual_duration = probe_duration(str(short_path))
    if actual_duration <= 0:
        actual_duration = clip_duration

    print(
        f"📱 Short gerado: {short_path.name} "
        f"({actual_duration:.1f}s, cena={scene_name}, peso={_scene_emotional_weight(best_scene):.1f})"
    )

    return {
        "path": str(short_path.resolve()),
        "duration": round(actual_duration, 2),
        "scene_name": scene_name,
    }


def maybe_extract_short(
    job_output_dir: Path | str,
    script_data: Any,
) -> Optional[dict]:
    """Executa extract_short quando USE_SHORTS_EXTRACTOR=true."""

    if not _is_enabled():
        return None

    try:
        return extract_short(job_output_dir, script_data)
    except Exception as exc:
        print(f"⚠️ Shorts extractor: {exc}")
        return None
