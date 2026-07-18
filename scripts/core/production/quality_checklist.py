"""
Quality Checklist — validação automática de qualidade dark antes de finalizar.

Bloqueia render/upload se itens críticos falharem.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.brand_engine import get_render_style
from scripts.core.production.logger import get_logger
from scripts.video.media_probe import probe_duration
from scripts.youtube.narration_utils import (
    DARK5_ITEM_KEYS,
    MAX_DURATION_SECONDS,
    MIN_DURATION_SECONDS,
    validate_hook_in_media_res,
    validate_scene_hooks,
    validate_sentence_length,
    validate_wtf_moments,
)


@dataclass
class ChecklistItem:
    name: str
    passed: bool
    message: str
    blocking: bool = True


@dataclass
class QualityChecklistReport:
    passed: bool
    phase: str
    items: List[ChecklistItem] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str, *, blocking: bool = True):
        self.items.append(ChecklistItem(name, passed, message, blocking))
        if not passed and blocking:
            self.failures.append(f"{name}: {message}")
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "phase": self.phase,
            "items": [
                {
                    "name": item.name,
                    "passed": item.passed,
                    "message": item.message,
                    "blocking": item.blocking,
                }
                for item in self.items
            ],
            "failures": self.failures,
        }


def _check_sentence_length(script: dict) -> ChecklistItem:
    warnings = validate_sentence_length(script)
    if warnings:
        return ChecklistItem(
            "sentence_length",
            False,
            f"{len(warnings)} frase(s) com mais de 12 palavras",
        )
    return ChecklistItem("sentence_length", True, "Todas as frases ≤12 palavras")


def _check_hook_media_res(script: dict) -> ChecklistItem:
    warnings = validate_hook_in_media_res(script)
    if warnings:
        return ChecklistItem("hook_in_media_res", False, warnings[0])
    return ChecklistItem("hook_in_media_res", True, "Hook começa in media res")


def _check_scene_hooks(script: dict) -> ChecklistItem:
    warnings = validate_scene_hooks(script)
    if warnings:
        return ChecklistItem(
            "scene_hooks",
            False,
            f"{len(warnings)} seção(ões) sem gancho de retenção",
        )
    return ChecklistItem("scene_hooks", True, "Ganchos presentes entre seções")


def _check_wtf_moments(script: dict) -> ChecklistItem:
    warnings = validate_wtf_moments(script)
    if not any(script.get(key) for key in DARK5_ITEM_KEYS):
        return ChecklistItem(
            "wtf_moments",
            True,
            "Template documentário — wtf moments não aplicável",
            blocking=False,
        )
    if warnings:
        return ChecklistItem(
            "wtf_moments",
            False,
            f"{len(warnings)} item(ns) sem momento perturbador",
        )
    return ChecklistItem("wtf_moments", True, "Cada item tem wtf moment")


def _check_soundtrack_present(export_folder: Optional[Path]) -> ChecklistItem:
    if export_folder is None:
        return ChecklistItem(
            "soundtrack_present",
            True,
            "Verificação de trilha adiada para pós-render",
            blocking=False,
        )

    soundtrack = export_folder / "assets" / "audio" / "soundtrack.mp3"
    if soundtrack.exists() and soundtrack.stat().st_size > 500:
        return ChecklistItem("soundtrack_present", True, "Trilha de fundo presente")
    return ChecklistItem(
        "soundtrack_present",
        False,
        "Trilha de fundo ausente ou inválida",
    )


def _check_color_grading_config(platform: str = "youtube_dark") -> ChecklistItem:
    style = get_render_style(platform)
    grade = style.color_grade or ""
    has_contrast = "contrast=" in grade
    has_saturation = "saturation=" in grade
    has_vignette = bool(style.vignette)

    if has_contrast and has_saturation and has_vignette:
        return ChecklistItem(
            "color_grading",
            True,
            "Color grading configurado no pipeline",
        )
    return ChecklistItem(
        "color_grading",
        False,
        "Color grading incompleto na configuração de render",
    )


def _check_duration(audio_duration: float) -> ChecklistItem:
    if audio_duration <= 0:
        return ChecklistItem(
            "duration",
            False,
            "Duração do áudio desconhecida",
        )

    minutes = audio_duration / 60
    if MIN_DURATION_SECONDS <= audio_duration <= MAX_DURATION_SECONDS:
        return ChecklistItem(
            "duration",
            True,
            f"Duração {minutes:.1f} min (8-15 min)",
        )

    return ChecklistItem(
        "duration",
        False,
        f"Duração {minutes:.1f} min fora do alvo (8-15 min)",
    )


def _check_soundtrack_in_video(export_folder: Path) -> ChecklistItem:
    video = export_folder / "video_final.mp4"
    if not video.exists():
        return ChecklistItem(
            "soundtrack_mixed",
            False,
            "Vídeo final ausente",
        )

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "json",
                str(video),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        data = json.loads(result.stdout or "{}")
        streams = data.get("streams", [])
        if streams:
            return ChecklistItem(
                "soundtrack_mixed",
                True,
                "Áudio mixado no vídeo final",
            )
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return ChecklistItem(
        "soundtrack_mixed",
        False,
        "Vídeo final sem faixa de áudio detectada",
    )


def run_pre_render_checklist(
    script: dict,
    *,
    audio_duration: float = 0.0,
    platform: str = "youtube_dark",
) -> QualityChecklistReport:
    """
    Checklist antes do render final — valida roteiro e configuração.
    Bloqueia render se algum item crítico falhar.
    """

    logger = get_logger("quality_checklist")
    report = QualityChecklistReport(passed=True, phase="pre_render")

    checks = [
        _check_hook_media_res(script),
        _check_sentence_length(script),
        _check_wtf_moments(script),
        _check_scene_hooks(script),
        _check_color_grading_config(platform),
    ]

    if audio_duration > 0:
        checks.append(_check_duration(audio_duration))

    for item in checks:
        report.add(item.name, item.passed, item.message, blocking=item.blocking)

    if report.passed:
        logger.success("Quality Checklist (pré-render): APROVADO")
    else:
        logger.error(
            "Quality Checklist (pré-render): REPROVADO",
            error="; ".join(report.failures[:5]),
        )

    return report


def run_post_render_checklist(
    export_folder: Path,
    result: Dict[str, Any],
    *,
    platform: str = "youtube_dark",
) -> QualityChecklistReport:
    """Checklist após render — valida trilha mixada e duração final."""

    logger = get_logger("quality_checklist")
    report = QualityChecklistReport(passed=True, phase="post_render")

    audio_ref = result.get("audio")
    audio_duration = 0.0
    if audio_ref and Path(audio_ref).exists():
        audio_duration = probe_duration(Path(audio_ref))
    elif (export_folder / "assets" / "audio" / "narracao.mp3").exists():
        audio_duration = probe_duration(
            export_folder / "assets" / "audio" / "narracao.mp3"
        )

    video = export_folder / "video_final.mp4"
    if video.exists():
        video_duration = probe_duration(video)
        if video_duration > 0:
            audio_duration = audio_duration or video_duration

    checks = [
        _check_soundtrack_present(export_folder),
        _check_soundtrack_in_video(export_folder),
        _check_color_grading_config(platform),
    ]

    if audio_duration > 0:
        checks.append(_check_duration(audio_duration))

    for item in checks:
        report.add(item.name, item.passed, item.message, blocking=item.blocking)

    report_path = export_folder / "quality_checklist_report.json"
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)

    if report.passed:
        logger.success("Quality Checklist (pós-render): APROVADO")
    else:
        logger.error(
            "Quality Checklist (pós-render): REPROVADO",
            error="; ".join(report.failures[:5]),
        )

    return report


def run_quality_checklist(
    script: dict,
    export_folder: Optional[Path] = None,
    result: Optional[Dict[str, Any]] = None,
    *,
    audio_duration: float = 0.0,
    phase: str = "pre_render",
    platform: str = "youtube_dark",
) -> QualityChecklistReport:
    """API unificada — delega para pré ou pós-render."""

    if phase == "post_render" and export_folder:
        return run_post_render_checklist(
            export_folder,
            result or {},
            platform=platform,
        )

    report = run_pre_render_checklist(
        script,
        audio_duration=audio_duration,
        platform=platform,
    )

    if export_folder:
        report_path = export_folder / "quality_checklist_report.json"
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)

    return report
