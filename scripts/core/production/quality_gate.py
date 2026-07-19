"""
Quality Gate — validação pré-render com bloqueio de publicação.

Gera quality_report.json com scores e explicação de aprovação/bloqueio.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional

from scripts.core.asset_rights_ledger import AssetRightsLedger
from scripts.core.production.logger import get_logger
from scripts.video.t2v_decision import MAX_T2V_SCENES

MIN_RESOLUTION_WIDTH = 1280
MIN_RESOLUTION_HEIGHT = 720
CRITICAL_MIN_WIDTH = 1920
CRITICAL_MIN_HEIGHT = 1080


@dataclass
class QualityGateReport:
    approved: bool
    blocked: bool
    block_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    publish_ready_score: float = 0.0
    visual_quality_score: float = 0.0
    rights_safety_score: float = 0.0
    monetization_risk_score: float = 0.0
    retention_score_estimate: float = 0.0
    metrics: dict = field(default_factory=dict)
    decisions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _load_media_search(export_folder: Path) -> dict:
    path = export_folder / "assets" / "media_search.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_retention(export_folder: Path) -> dict:
    path = export_folder / "retention_report.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _compute_media_metrics(media_data: dict, scenes: list) -> dict:
    total = len(scenes) or len(media_data.get("scenes", [])) or 1
    scene_results = media_data.get("scenes", [])

    real_video = sum(1 for s in scene_results if s.get("media_type") == "video")
    static_image = sum(1 for s in scene_results if s.get("media_type") == "image")
    ai_image = sum(1 for s in scene_results if s.get("media_type", "").startswith("ai_image"))
    ai_video = sum(1 for s in scene_results if s.get("media_type") in ("ai_video", "t2v"))
    editorial = sum(1 for s in scene_results if str(s.get("media_type", "")).startswith("editorial"))
    t2v_count = sum(1 for s in scene_results if s.get("provedor") in ("replicate", "n8n", "fal", "kling") or s.get("media_type") == "ai_video")

    providers = {s.get("provedor") for s in scene_results if s.get("provedor")}
    no_asset = sum(1 for s in scene_results if not s.get("saved"))
    low_relevance = sum(1 for s in scene_results if float(s.get("quality_score", 0)) < 0.35)

    # Repetição visual — mesma fonte consecutiva
    sources = [s.get("provedor") for s in scene_results if s.get("saved")]
    repeated = 0
    for i in range(1, len(sources)):
        if sources[i] == sources[i - 1]:
            repeated += 1

    durations = [float(s.get("duration_seconds", 0)) for s in scenes if s.get("duration_seconds")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total_scenes": total,
        "real_video_pct": round(real_video / total * 100, 1),
        "static_image_pct": round(static_image / total * 100, 1),
        "ai_image_pct": round(ai_image / total * 100, 1),
        "t2v_pct": round(t2v_count / total * 100, 1),
        "editorial_fallback_pct": round(editorial / total * 100, 1),
        "t2v_count": t2v_count,
        "provider_diversity": len(providers),
        "visual_repetition_count": repeated,
        "scenes_without_asset": no_asset,
        "low_relevance_scenes": low_relevance,
        "avg_scene_duration": round(avg_duration, 1),
    }


def _quality_gate_enabled() -> bool:
    return os.getenv("QUALITY_GATE_ENABLED", "true").lower() not in ("false", "0", "no")


def run_quality_gate(
    export_folder: Path,
    result: dict,
    *,
    block_on_failure: bool = True,
    ledger: Optional[AssetRightsLedger] = None,
) -> QualityGateReport:
    """
    Valida qualidade editorial, direitos e risco de monetização antes do render.
    """

    logger = get_logger("quality_gate")
    export_folder = Path(export_folder)

    if not _quality_gate_enabled():
        report = QualityGateReport(approved=True, blocked=False)
        report.decisions.append("SKIPPED — QUALITY_GATE_ENABLED=false")
        report_path = export_folder / "quality_report.json"
        report_path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Quality Gate: desabilitado (QUALITY_GATE_ENABLED=false)")
        return report

    report = QualityGateReport(approved=True, blocked=False)

    media_data = _load_media_search(export_folder)
    scenes = result.get("cenas", {}).get("cenas", []) if isinstance(result.get("cenas"), dict) else []
    metrics = _compute_media_metrics(media_data, scenes)
    report.metrics = metrics

    # --- Bloqueios hard ---
    if ledger is None:
        ledger = AssetRightsLedger(export_folder)

    unsafe = ledger.get_unsafe_assets()
    if unsafe:
        report.blocked = True
        report.block_reasons.append(
            f"{len(unsafe)} asset(s) with unsafe/unverified license"
        )

    if metrics["t2v_count"] > MAX_T2V_SCENES:
        report.blocked = True
        report.block_reasons.append(
            f"T2V limit exceeded: {metrics['t2v_count']}/{MAX_T2V_SCENES}"
        )

    if metrics["scenes_without_asset"] > 0:
        report.blocked = True
        report.block_reasons.append(
            f"{metrics['scenes_without_asset']} scene(s) without asset"
        )

    # Disabled — blocked valid Wikimedia-only footage (same provider per scene)
    # if metrics["visual_repetition_count"] > len(scenes) // 2:
    #     report.blocked = True
    #     report.block_reasons.append("Excessive visual repetition — looks mass-produced")

    # Watermark check via media metadata
    for scene_result in media_data.get("scenes", []):
        if scene_result.get("has_watermark"):
            report.blocked = True
            report.block_reasons.append(f"Watermark detected in scene {scene_result.get('scene')}")

    # Low resolution critical
    for scene_result in media_data.get("scenes", []):
        w = scene_result.get("width", 0)
        h = scene_result.get("height", 0)
        if w and h and (w < MIN_RESOLUTION_WIDTH or h < MIN_RESOLUTION_HEIGHT):
            report.blocked = True
            report.block_reasons.append(
                f"Critical low resolution in scene {scene_result.get('scene')}: {w}x{h}"
            )

    # --- Warnings ---
    if metrics["real_video_pct"] < 20 and metrics["editorial_fallback_pct"] < 30:
        report.warnings.append("Low real footage — heavy on static/AI content")

    if metrics["ai_image_pct"] > 50:
        report.warnings.append("More than 50% AI images — monetization risk")

    if metrics["t2v_count"] == MAX_T2V_SCENES:
        report.warnings.append(f"T2V at maximum limit ({MAX_T2V_SCENES} scenes)")

    if metrics["low_relevance_scenes"] > 2:
        report.warnings.append(f"{metrics['low_relevance_scenes']} scenes with low relevance")

    reused_risk = metrics["static_image_pct"] > 70 and metrics["real_video_pct"] < 10
    if reused_risk:
        report.warnings.append("High reused content risk — mostly static images")

    # --- Scores ---
    report.visual_quality_score = min(100.0, (
        metrics["real_video_pct"] * 0.35
        + metrics["editorial_fallback_pct"] * 0.25
        + (100 - metrics["ai_image_pct"]) * 0.20
        + (100 - metrics["static_image_pct"]) * 0.10
        + min(100, metrics["provider_diversity"] * 15)
    ))

    report.rights_safety_score = 100.0 if ledger.all_safe() else max(
        0.0, 100.0 - len(unsafe) * 25
    )

    report.monetization_risk_score = max(0.0, 100.0 - (
        metrics["ai_image_pct"] * 0.4
        + metrics["t2v_pct"] * 0.3
        + (100 - metrics["real_video_pct"]) * 0.15
        + metrics["visual_repetition_count"] * 5
    ))

    retention_data = _load_retention(export_folder)
    report.retention_score_estimate = float(retention_data.get("overall_score", 65))

    report.publish_ready_score = round(
        report.visual_quality_score * 0.30
        + report.rights_safety_score * 0.25
        + report.monetization_risk_score * 0.25
        + report.retention_score_estimate * 0.20,
        1,
    )

    if report.publish_ready_score < 60:
        report.warnings.append(f"Publish ready score below 60: {report.publish_ready_score}")

    report.approved = not report.blocked and report.publish_ready_score >= 55

    if report.approved:
        report.decisions.append(
            f"APPROVED — publish_ready={report.publish_ready_score}, "
            f"real_video={metrics['real_video_pct']}%, t2v={metrics['t2v_count']}"
        )
    else:
        report.decisions.append(
            f"BLOCKED — {'; '.join(report.block_reasons[:3]) or 'score too low'}"
        )

    report_path = export_folder / "quality_report.json"
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    if report.approved:
        logger.success(f"Quality Gate: APROVADO ({report.publish_ready_score}/100)")
    else:
        logger.error(
            f"Quality Gate: BLOQUEADO — {'; '.join(report.block_reasons[:3])}",
        )

    if block_on_failure and report.blocked:
        raise RuntimeError(
            f"Quality Gate bloqueou render: {'; '.join(report.block_reasons[:5])}"
        )

    return report
