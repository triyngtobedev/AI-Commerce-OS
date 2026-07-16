"""
Health check pré-upload.

Valida integridade do pacote de produção antes de publicar.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.brand_validation import validate_brand_asset
from scripts.core.production.logger import get_logger


@dataclass
class HealthCheckReport:
    valid: bool
    checks: List[dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str, *, severity: str = "error"):
        self.checks.append({
            "check": name,
            "passed": passed,
            "message": message,
            "severity": severity,
        })
        if passed:
            return
        if severity == "warning":
            self.warnings.append(f"{name}: {message}")
        else:
            self.errors.append(f"{name}: {message}")
            self.valid = False

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _probe_video(path: Path) -> Optional[dict]:
    """Obtém metadados do vídeo via ffprobe."""

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def _get_video_stream(probe: dict) -> Optional[dict]:
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    return None


def run_health_check(
    export_folder: Path,
    result: Dict[str, Any],
    *,
    min_duration: float = 60.0,
    expected_width: int = 1920,
    expected_height: int = 1080,
    expected_fps: float = 30.0,
    fps_tolerance: float = 1.0,
) -> HealthCheckReport:
    """
    Executa validação completa antes do upload.

    Retorna relatório detalhado. Upload deve ser bloqueado se valid=False.
    """

    logger = get_logger("health_check")
    logger.stage_start()

    report = HealthCheckReport(valid=True)
    conteudo = result.get("conteudo", {}) or {}
    youtube_meta = result.get("youtube_metadata", {}) or {}

    # Thumbnail
    thumbnail = youtube_meta.get("thumbnail") or (export_folder / "thumbnail.jpg")
    thumb_path = Path(str(thumbnail)) if thumbnail else None
    if thumb_path and thumb_path.exists():
        thumb_report = validate_brand_asset(thumb_path, "thumbnail")
        report.add("thumbnail_exists", True, str(thumb_path))
        report.add(
            "thumbnail_valid",
            thumb_report.valid,
            "; ".join(thumb_report.messages) or "Thumbnail válida",
            severity="error" if not thumb_report.valid else "warning",
        )
    else:
        report.add("thumbnail_exists", False, "Thumbnail não encontrada")

    # Áudio
    audio_path = result.get("audio")
    if audio_path and Path(audio_path).exists():
        report.add("audio_exists", True, str(audio_path))
    else:
        audio_candidate = export_folder / "assets" / "audio" / "narracao.mp3"
        if audio_candidate.exists():
            report.add("audio_exists", True, str(audio_candidate))
        else:
            report.add("audio_exists", False, "Arquivo de áudio não encontrado")

    # Vídeo
    video_path = result.get("video")
    final_video = export_folder / "video_final.mp4"
    resolved_video = None

    if video_path and Path(video_path).exists():
        resolved_video = Path(video_path)
    elif final_video.exists():
        resolved_video = final_video

    if resolved_video:
        report.add("video_exists", True, str(resolved_video))

        probe = _probe_video(resolved_video)
        if probe:
            stream = _get_video_stream(probe)
            duration = float(probe.get("format", {}).get("duration", 0))
            report.add(
                "duration_valid",
                duration >= min_duration,
                f"Duração: {duration:.1f}s (mínimo: {min_duration}s)",
            )

            if stream:
                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
                report.add(
                    "resolution_correct",
                    width >= expected_width and height >= expected_height,
                    f"Resolução: {width}x{height} (esperado: {expected_width}x{expected_height})",
                )

                fps_str = stream.get("r_frame_rate", "0/1")
                try:
                    num, den = fps_str.split("/")
                    fps = float(num) / float(den) if float(den) else 0
                except (ValueError, ZeroDivisionError):
                    fps = 0

                report.add(
                    "fps_correct",
                    abs(fps - expected_fps) <= fps_tolerance,
                    f"FPS: {fps:.2f} (esperado: {expected_fps})",
                    severity="warning",
                )
        else:
            report.add(
                "video_probe",
                False,
                "Não foi possível analisar vídeo (ffprobe indisponível ou falhou)",
                severity="warning",
            )
    else:
        report.add("video_exists", False, "Vídeo final não encontrado")

    # Legendas
    subtitle = result.get("subtitle_file")
    if subtitle and Path(subtitle).exists():
        report.add("subtitles_exist", True, str(subtitle))
    else:
        report.add(
            "subtitles_exist",
            False,
            "Legendas não encontradas",
            severity="warning",
        )

    # Metadados
    titulo = str(conteudo.get("titulo", "")).strip()
    report.add(
        "title_valid",
        len(titulo) >= 5 and len(titulo) <= 100,
        f"Título: '{titulo[:50]}...' ({len(titulo)} chars)" if len(titulo) > 50 else f"Título: '{titulo}' ({len(titulo)} chars)",
    )

    descricao = str(conteudo.get("descricao", "")).strip()
    report.add(
        "description_valid",
        len(descricao) >= 20,
        f"Descrição: {len(descricao)} caracteres",
    )

    tags = conteudo.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    report.add(
        "tags_valid",
        len(tags) >= 3,
        f"Tags: {len(tags)} (mínimo: 3)",
        severity="warning" if len(tags) < 3 else "error",
    )

    idioma = conteudo.get("idioma", "pt-BR")
    report.add(
        "language_valid",
        bool(idioma),
        f"Idioma: {idioma}",
    )

    categoria = conteudo.get("categoria_youtube", youtube_meta.get("categoria", ""))
    report.add(
        "category_valid",
        bool(categoria),
        f"Categoria: {categoria or 'ausente'}",
    )

    # Timeline consistente
    cenas = result.get("cenas", {})
    scene_list = cenas.get("cenas", []) if isinstance(cenas, dict) else cenas
    report.add(
        "timeline_consistent",
        len(scene_list) >= 3,
        f"Cenas na timeline: {len(scene_list)}",
    )

    # Branding — post_package
    post_package_path = export_folder / "post_package.json"
    if post_package_path.exists():
        report.add("metadata_complete", True, "post_package.json presente")
    else:
        report.add("metadata_complete", False, "post_package.json ausente")

    # Salvar relatório
    report_path = export_folder / "health_check_report.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)

    if report.valid:
        logger.success("Health check aprovado")
    else:
        logger.error(
            f"Health check reprovado — {len(report.errors)} erro(s)",
            error="; ".join(report.errors[:3]),
        )

    return report
