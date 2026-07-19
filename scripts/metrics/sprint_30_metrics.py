"""
Sprint 30 Metrics — append-only JSONL para comparar baseline vs sprint.

Arquivo: sprint_30_metrics.jsonl (raiz do repo)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from scripts.core.feature_flags import sprint30_flags_snapshot, sprint30_metrics

METRICS_FILE = Path("sprint_30_metrics.jsonl")


def _read_json(path: Path) -> Optional[dict | list]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _avg_visual_relevance(assets_dir: Path) -> Optional[float]:
    data = _read_json(assets_dir / "media_search.json")
    if not isinstance(data, dict):
        return None

    scores = []
    for scene in data.get("scenes", []):
        if not scene.get("saved"):
            continue
        if scene.get("visual_score") is not None:
            scores.append(float(scene["visual_score"]))
        elif scene.get("quality_score") is not None:
            scores.append(float(scene["quality_score"]) * 100)

    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)


def _thumbnail_metrics(output_dir: Path) -> dict[str, Any]:
    report = _read_json(output_dir / "thumbnail_ab_report.json")
    if not isinstance(report, dict):
        thumb = output_dir / "thumbnail.jpg"
        return {
            "thumbnail_variant": None,
            "thumbnail_ctr_estimate": None,
            "thumbnail_present": thumb.exists(),
        }

    winner = report.get("winner") or {}
    scores = winner.get("scores") or {}
    return {
        "thumbnail_variant": winner.get("variant"),
        "thumbnail_ctr_estimate": scores.get("ctr_estimate"),
        "thumbnail_text_legibility": scores.get("text_legibility"),
        "thumbnail_present": bool(report.get("final_thumbnail")),
    }


def _retention_predictions(retention_report: dict) -> dict[str, Optional[float]]:
    base = float(retention_report.get("overall_score", 50))
    hook = float(retention_report.get("hook_strength", 50))
    slow_penalty = len(retention_report.get("slow_scenes") or []) * 4
    rep_penalty = len(retention_report.get("repetitions") or []) * 2

    return {
        "retention_predicted_30s": round(min(100.0, hook * 0.92 + base * 0.08), 2),
        "retention_predicted_60s": round(min(100.0, base * 0.88 - slow_penalty * 0.5), 2),
        "retention_predicted_180s": round(min(100.0, base * 0.78 - slow_penalty), 2),
        "retention_predicted_360s": round(min(100.0, base * 0.68 - slow_penalty - rep_penalty), 2),
        "retention_overall_score": round(base, 2),
    }


def _audio_metrics(output_dir: Path, result: dict) -> dict[str, Any]:
    audio_layer = result.get("audio_layer") or {}
    final_audio = output_dir / "assets" / "audio" / "final_audio.mp3"
    soundtrack = output_dir / "assets" / "audio" / "soundtrack.mp3"
    narration = output_dir / "assets" / "audio" / "narracao.mp3"

    has_track = soundtrack.exists() or bool(audio_layer.get("soundtrack"))
    has_sfx = int(audio_layer.get("sfx_events", 0)) > 0
    has_final = final_audio.exists()

    return {
        "audio_track_present": has_track,
        "audio_sfx_present": has_sfx,
        "audio_layer_adequate": has_final and (has_track or has_sfx),
        "audio_sfx_count": int(audio_layer.get("sfx_events", 0)),
    }


def build_metrics_record(
    *,
    topic: str,
    output_dir: Path,
    result: dict,
    retention_report: Optional[dict] = None,
    video_produced: bool = False,
) -> dict[str, Any]:
    assets_dir = output_dir / "assets"
    retention = retention_report or _read_json(output_dir / "retention_report.json") or {}

    record: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "output_dir": str(output_dir),
        "video_produced": video_produced,
        "feature_flags": sprint30_flags_snapshot(),
        "visual_relevance_avg": _avg_visual_relevance(assets_dir),
    }
    record.update(_thumbnail_metrics(output_dir))
    record.update(_retention_predictions(retention if isinstance(retention, dict) else {}))
    record.update(_audio_metrics(output_dir, result))

    actions = _read_json(output_dir / "retention_actions.json")
    if isinstance(actions, dict):
        record["retention_actions_count"] = len(actions.get("actions") or [])

    return record


def append_metrics(record: dict[str, Any], *, path: Path | None = None) -> Path:
    target = path or METRICS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target


def record_sprint_30_metrics(
    *,
    topic: str,
    output_dir: Path,
    result: dict,
    retention_report: Optional[dict] = None,
    video_produced: bool = False,
) -> Optional[Path]:
    if not sprint30_metrics():
        return None

    record = build_metrics_record(
        topic=topic,
        output_dir=output_dir,
        result=result,
        retention_report=retention_report,
        video_produced=video_produced,
    )
    path = append_metrics(record)
    print(f"📊 Sprint 30 metrics → {path}")
    return path
