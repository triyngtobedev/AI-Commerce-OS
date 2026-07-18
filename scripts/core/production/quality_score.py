"""
Quality Score — avaliação automática pré-upload.

Bloqueia publicação se a nota ficar abaixo do mínimo configurado.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.brand_kit import score_image_contrast
from scripts.core.production.health_check import _probe_video, _get_video_stream
from scripts.core.production.logger import get_logger
from scripts.video.media_probe import probe_duration
from scripts.video.scene_timeline import extract_scenes, resolve_scene_media
from scripts.video.subtitle_engine import validate_srt_timing

MIN_QUALITY_SCORE = 70.0

_WEIGHTS = {
    "visual_quality": 0.20,
    "media_richness": 0.15,
    "motion_coverage": 0.10,
    "caption_quality": 0.15,
    "audio_sync": 0.10,
    "soundtrack": 0.10,
    "thumbnail": 0.10,
    "rhythm": 0.10,
}


@dataclass
class QualityScoreReport:
    score: float
    passed: bool
    min_score: float
    dimensions: List[dict] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_dimension(self, name: str, score: float, weight: float, detail: str):
        self.dimensions.append({
            "dimension": name,
            "score": round(score, 1),
            "weight": weight,
            "weighted": round(score * weight, 1),
            "detail": detail,
        })

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "passed": self.passed,
            "min_score": self.min_score,
            "dimensions": self.dimensions,
            "failures": self.failures,
            "warnings": self.warnings,
        }


def _score_visual_quality(export_folder: Path, result: dict) -> tuple[float, str]:
    media_search = export_folder / "assets" / "media_search.json"
    if not media_search.exists():
        return 50.0, "media_search.json ausente"

    data = json.loads(media_search.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    if not scenes:
        return 40.0, "sem dados de cena"

    scores = [float(s.get("quality_score", 0)) for s in scenes if s.get("saved")]
    video_count = sum(1 for s in scenes if s.get("media_type") == "video")
    total = len(scenes) or 1

    avg = sum(scores) / len(scores) if scores else 0.3
    video_ratio = video_count / total

    score = min(100.0, avg * 120 + video_ratio * 30)
    return score, f"avg_quality={avg:.2f}, videos={video_count}/{total}"


def _score_media_richness(export_folder: Path, result: dict) -> tuple[float, str]:
    scenes = extract_scenes(result.get("cenas", {}))
    assets_root = export_folder / "assets"
    sources = set()

    for index in range(len(scenes)):
        media = resolve_scene_media(assets_root, index, len(scenes))
        if media:
            sources.add(media.name)

    unique_ratio = len(sources) / len(scenes) if scenes else 0
    score = min(100.0, unique_ratio * 100)
    return score, f"assets_únicos={len(sources)}/{len(scenes)}"


def _score_motion_coverage(result: dict) -> tuple[float, str]:
    scenes = extract_scenes(result.get("cenas", {}))
    if not scenes:
        return 50.0, "sem cenas"

    with_motion = sum(
        1 for s in scenes
        if s.get("scene_motion") or s.get("camera_motion") or s.get("visual_spec")
    )
    ratio = with_motion / len(scenes)
    score = min(100.0, ratio * 100)
    return score, f"cenas_com_motion={with_motion}/{len(scenes)}"


def _score_captions(export_folder: Path, result: dict) -> tuple[float, str]:
    srt_path = export_folder / "captions.srt"
    if not srt_path.exists():
        return 0.0, "legendas ausentes"

    content = srt_path.read_text(encoding="utf-8")
    cenas = result.get("cenas", {})
    audio_duration = float(cenas.get("audio_duration", 0)) if isinstance(cenas, dict) else 0

    if audio_duration <= 0:
        audio_ref = result.get("audio")
        if audio_ref and Path(audio_ref).exists():
            audio_duration = probe_duration(Path(audio_ref))

    ok, reason = validate_srt_timing(content, audio_duration, tolerance=2.0)
    if not ok:
        return 40.0, reason

    blocks = re.findall(
        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
        content,
    )
    long_blocks = 0
    for start, end in blocks:
        from scripts.video.subtitle_engine import _parse_srt_time
        duration = _parse_srt_time(end) - _parse_srt_time(start)
        if duration > 4.5:
            long_blocks += 1

    penalty = min(30, long_blocks * 5)
    score = max(60.0, 95.0 - penalty)
    return score, f"blocos={len(blocks)}, longos={long_blocks}"


def _score_audio_sync(export_folder: Path, result: dict) -> tuple[float, str]:
    video = export_folder / "video_final.mp4"
    audio_ref = result.get("audio")
    if not video.exists() or not audio_ref:
        return 50.0, "vídeo ou áudio ausente"

    video_dur = probe_duration(video)
    audio_dur = probe_duration(Path(audio_ref))
    delta = abs(video_dur - audio_dur)

    if delta <= 0.5:
        return 100.0, f"delta={delta:.2f}s"
    if delta <= 1.0:
        return 85.0, f"delta={delta:.2f}s"
    if delta <= 2.0:
        return 60.0, f"delta={delta:.2f}s"
    return 30.0, f"delta={delta:.2f}s (fora do limite)"


def _score_soundtrack(export_folder: Path) -> tuple[float, str]:
    soundtrack = export_folder / "assets" / "audio" / "soundtrack.mp3"
    if not soundtrack.exists():
        return 0.0, "trilha ausente"

    video = export_folder / "video_final.mp4"
    if not video.exists():
        return 70.0, "trilha presente, vídeo não verificado"

    probe = _probe_video(video)
    if not probe:
        return 70.0, "trilha presente"

    has_audio = any(s.get("codec_type") == "audio" for s in probe.get("streams", []))
    if has_audio:
        return 100.0, "trilha mixada no vídeo final"
    return 50.0, "trilha gerada mas não detectada no vídeo"


def _score_thumbnail(export_folder: Path, result: dict) -> tuple[float, str]:
    thumb = export_folder / "thumbnail.jpg"
    youtube_meta = result.get("youtube_metadata", {}) or {}
    thumb_ref = youtube_meta.get("thumbnail")
    if thumb_ref:
        thumb = Path(str(thumb_ref))

    if not thumb.exists():
        return 0.0, "thumbnail ausente"

    contrast = score_image_contrast(thumb)
    if contrast >= 60:
        return 95.0, f"contraste={contrast:.1f}"
    if contrast >= 40:
        return 75.0, f"contraste={contrast:.1f}"
    if contrast >= 25:
        return 55.0, f"contraste={contrast:.1f}"
    return 35.0, f"contraste baixo={contrast:.1f}"


def _score_rhythm(result: dict) -> tuple[float, str]:
    scenes = extract_scenes(result.get("cenas", {}))
    durations = [
        float(s.get("duration_seconds", 0))
        for s in scenes
        if isinstance(s, dict) and s.get("duration_seconds")
    ]
    if not durations:
        return 50.0, "durações indisponíveis"

    max_dur = max(durations)
    avg_dur = sum(durations) / len(durations)
    long_scenes = sum(1 for d in durations if d > 20)

    score = 100.0
    if max_dur > 25:
        score -= 25
    elif max_dur > 20:
        score -= 10
    if long_scenes > 2:
        score -= 15
    if avg_dur > 18:
        score -= 10

    short_scenes = sum(1 for d in durations if d < 15)
    if short_scenes > 2:
        score -= 10

    variance = max(durations) - min(durations)
    if variance < 5:
        score -= 15

    return max(30.0, score), f"max={max_dur:.0f}s, avg={avg_dur:.0f}s, longas={long_scenes}"


def run_quality_score(
    export_folder: Path,
    result: Dict[str, Any],
    *,
    min_score: float = MIN_QUALITY_SCORE,
) -> QualityScoreReport:
    """Executa avaliação completa de qualidade do vídeo."""

    logger = get_logger("quality_score")
    report = QualityScoreReport(score=0.0, passed=False, min_score=min_score)

    scorers = [
        ("visual_quality", _score_visual_quality),
        ("media_richness", _score_media_richness),
        ("motion_coverage", lambda f, r: _score_motion_coverage(r)),
        ("caption_quality", _score_captions),
        ("audio_sync", _score_audio_sync),
        ("soundtrack", lambda f, r: _score_soundtrack(f)),
        ("thumbnail", _score_thumbnail),
        ("rhythm", lambda f, r: _score_rhythm(r)),
    ]

    total = 0.0
    for name, scorer in scorers:
        try:
            dim_score, detail = scorer(export_folder, result)
        except Exception as exc:
            dim_score, detail = 40.0, f"erro: {exc}"

        weight = _WEIGHTS[name]
        report.add_dimension(name, dim_score, weight, detail)
        total += dim_score * weight

        if dim_score < 50:
            report.failures.append(f"{name}: {detail}")
        elif dim_score < 70:
            report.warnings.append(f"{name}: {detail}")

    report.score = round(total, 1)
    report.passed = report.score >= min_score and len(report.failures) <= 2

    report_path = export_folder / "quality_score_report.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)

    if report.passed:
        logger.success(f"Quality Score: {report.score}/100 — APROVADO")
    else:
        logger.error(
            f"Quality Score: {report.score}/100 — REPROVADO (mín: {min_score})",
            error="; ".join(report.failures[:3]),
        )

    return report
