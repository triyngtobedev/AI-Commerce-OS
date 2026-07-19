"""Coleta e persistência de métricas Sprint 30 (JSONL)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from scripts.core.brand_kit import score_image_contrast
from scripts.sprint30.config import get_flags, get_metrics_path, is_sprint30_enabled
from scripts.sprint30.retention_controller import predict_retention
from scripts.utils.slug import content_output_dir, slugify

_BATCH_ID: str | None = None


def set_batch_id(batch_id: str) -> None:
    global _BATCH_ID
    _BATCH_ID = batch_id


def get_batch_id() -> str:
    global _BATCH_ID
    if _BATCH_ID is None:
        _BATCH_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    return _BATCH_ID


def append_sprint30_metrics(record: dict) -> Path:
    path = get_metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def build_sprint30_record(
    *,
    topic: dict,
    result: dict | None,
    export_folder: Path | None,
    status: str,
    upload_result: dict | None = None,
    perf_report: dict | None = None,
    health_report: dict | None = None,
    quality_report: dict | None = None,
    failure_stage: str | None = None,
    failure_reason: str | None = None,
    tts_provider: str | None = None,
) -> dict:
    topic_name = str(topic.get("nome", ""))
    slug = slugify(topic_name)
    platform = result.get("platform", "youtube_dark") if result else "youtube_dark"

    media_stats = _media_stats(export_folder)
    quality = quality_report or _load_json(export_folder / "quality_score_report.json") if export_folder else None
    health = health_report or _load_json(export_folder / "health_check_report.json") if export_folder else None
    retention = predict_retention(
        export_folder or Path("."),
        result or {"cenas": {}},
        quality_report=quality,
        health_report=health,
    )

    thumbnail_path = _resolve_thumbnail(export_folder, result)
    audio_layers = _audio_layer_stats(export_folder, result)

    record: dict[str, Any] = {
        "sprint": "30",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "batch_id": get_batch_id(),
        "topic_name": topic_name,
        "topic_slug": slug,
        "platform": platform,
        "template": _resolve_template(result),
        "status": status,
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "pipeline_mode": "production",
        "duration_seconds": _total_duration(perf_report),
        "step_timings": (perf_report or {}).get("step_timings", {}),
        "providers": {
            "tts": tts_provider or _infer_tts_provider(result),
            "media_engine": media_stats.get("engine", "visual_engine"),
        },
        "media_stats": media_stats,
        "visual_relevance_avg": media_stats.get("avg_quality_score", 0.0),
        "thumbnail_ctr_estimate": _thumbnail_ctr_estimate(thumbnail_path),
        "audio_layer_adequate": audio_layers["adequate"],
        "audio_sfx_count": audio_layers["sfx_count"],
        "quality_score": (quality or {}).get("score"),
        "quality_passed": (quality or {}).get("passed"),
        "health_valid": (health or {}).get("valid"),
        "upload_status": (upload_result or {}).get("status"),
        "video_id": (upload_result or {}).get("video_id"),
        "video_url": (upload_result or {}).get("video_url"),
        "video_path": result.get("video") if result else None,
        "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
        "flags": get_flags(),
        **retention,
    }
    return record


def record_sprint30_from_context(
    ctx: Any,
    *,
    status: str,
    upload_result: dict | None = None,
    perf_report: dict | None = None,
    failure_stage: str | None = None,
    failure_reason: str | None = None,
) -> Optional[Path]:
    if not is_sprint30_enabled():
        return None

    topic = ctx.data.get("topic", {})
    export_folder = ctx.data.get("export_folder") or ctx.output_dir
    result = None
    if "pipeline_result" in ctx.data:
        result = ctx.data["pipeline_result"].to_dict()

    health_report = None
    quality_report = None
    if hasattr(ctx.data.get("health_report"), "to_dict"):
        health_report = ctx.data["health_report"].to_dict()
    if hasattr(ctx.data.get("quality_report"), "to_dict"):
        quality_report = ctx.data["quality_report"].to_dict()

    tts_provider = None
    audio_meta = (result or {}).get("audio_metadata") or {}
    tts_provider = audio_meta.get("provider")

    record = build_sprint30_record(
        topic=topic,
        result=result,
        export_folder=Path(export_folder) if export_folder else None,
        status=status,
        upload_result=upload_result,
        perf_report=perf_report,
        health_report=health_report,
        quality_report=quality_report,
        failure_stage=failure_stage,
        failure_reason=failure_reason,
        tts_provider=tts_provider,
    )
    return append_sprint30_metrics(record)


def revalidate_export_folder(topic: dict, export_folder: Path) -> dict | None:
    """Reavalia um export existente (health + quality) e grava métricas Sprint 30."""

    video = export_folder / "video_final.mp4"
    if not video.exists():
        return None

    from scripts.core.production.health_check import run_health_check
    from scripts.core.production.quality_score import run_quality_score

    result = _load_pipeline_result_from_folder(topic, export_folder)
    health = run_health_check(export_folder, result)
    quality = run_quality_score(export_folder, result)

    perf_report = {}
    perf_path = export_folder / "performance_report.json"
    if perf_path.exists():
        perf_report = _load_json(perf_path) or {}

    record = build_sprint30_record(
        topic=topic,
        result=result,
        export_folder=export_folder,
        status="completed",
        upload_result={"status": "SKIPPED", "message": "revalidate-only"},
        perf_report=perf_report,
        health_report=health.to_dict(),
        quality_report=quality.to_dict(),
    )
    append_sprint30_metrics(record)
    return record


def _load_pipeline_result_from_folder(topic: dict, export_folder: Path) -> dict:
    scenes = _load_json(export_folder / "scenes.json") or {}
    content = _load_json(export_folder / "content.json") or {}
    strategy = _load_json(export_folder / "strategy.json") or {}
    thumb = export_folder / "thumbnail.jpg"

    return {
        "produto": topic,
        "conteudo": content,
        "estrategia": strategy,
        "cenas": scenes,
        "audio": str(export_folder / "assets" / "audio" / "narracao.mp3"),
        "video": str(export_folder / "video_final.mp4"),
        "platform": "youtube_dark",
        "youtube_metadata": {
            "thumbnail": str(thumb) if thumb.exists() else None,
        },
    }


def summarize_metrics_file(path: Path | None = None) -> dict:
    target = path or get_metrics_path()
    if not target.exists():
        return {"count": 0, "batch_id": get_batch_id()}

    rows = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    batch_id = get_batch_id()
    batch_rows = [row for row in rows if row.get("batch_id") == batch_id]
    if not batch_rows:
        batch_rows = rows[-8:]

    completed = [row for row in batch_rows if row.get("status") == "completed"]
    failed = [row for row in batch_rows if row.get("status") == "failed"]

    def _avg(key: str) -> float | None:
        values = [float(row[key]) for row in completed if row.get(key) is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 3)

    return {
        "batch_id": batch_id,
        "count": len(batch_rows),
        "completed": len(completed),
        "failed": len(failed),
        "visual_relevance_avg": _avg("visual_relevance_avg"),
        "thumbnail_ctr_estimate_avg": _avg("thumbnail_ctr_estimate"),
        "retention_predicted_score_avg": _avg("retention_predicted_score"),
        "audio_layer_adequate_rate": _rate(completed, "audio_layer_adequate"),
        "audio_sfx_count_avg": _avg("audio_sfx_count"),
        "retention_actions_count_avg": _avg("retention_actions_count"),
        "metrics_path": str(target),
    }


def _rate(rows: list[dict], key: str) -> float | None:
    if not rows:
        return None
    ok = sum(1 for row in rows if row.get(key))
    return round(ok / len(rows), 3)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _media_stats(export_folder: Path | None) -> dict:
    if not export_folder:
        return {
            "scenes_total": 0,
            "video_scenes": 0,
            "image_scenes": 0,
            "avg_quality_score": 0.0,
            "t2v_used": 0,
            "engine": "unknown",
        }

    data = _load_json(export_folder / "assets" / "media_search.json") or {}
    scenes = data.get("scenes", [])
    video_types = {"video", "ai_video"}
    image_types = {"image", "photo"}

    video_scenes = sum(1 for s in scenes if s.get("media_type") in video_types)
    image_scenes = sum(1 for s in scenes if s.get("media_type") in image_types)
    scores = [float(s.get("quality_score", 0)) for s in scenes if s.get("saved")]
    t2v_used = sum(1 for s in scenes if s.get("media_type") == "ai_video")

    return {
        "scenes_total": len(scenes),
        "video_scenes": video_scenes,
        "image_scenes": image_scenes,
        "avg_quality_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "t2v_used": t2v_used,
        "engine": data.get("engine", "visual_engine"),
    }


def _audio_layer_stats(export_folder: Path | None, result: dict | None) -> dict:
    if not export_folder:
        return {"adequate": False, "sfx_count": 0}

    narration = export_folder / "assets" / "audio" / "narracao.mp3"
    soundtrack = export_folder / "assets" / "audio" / "soundtrack.mp3"
    adequate = narration.exists() and soundtrack.exists()

    sfx_count = 0
    cenas = (result or {}).get("cenas", {}).get("cenas", [])
    if isinstance(cenas, list):
        for scene in cenas:
            hints = (scene or {}).get("effect_hints") or {}
            hint = hints.get("soundtrack_hint", "")
            if hint in {"dramatic_stinger", "tension_rising"}:
                sfx_count += 1
            if hints.get("flash_enabled") or hints.get("shake_enabled"):
                sfx_count += 1

    return {"adequate": adequate, "sfx_count": sfx_count}


def _thumbnail_ctr_estimate(thumbnail_path: Path | None) -> float | None:
    if not thumbnail_path or not thumbnail_path.exists():
        return None
    contrast = score_image_contrast(thumbnail_path)
    # Heurística 0–1: contraste alto correlaciona com CTR em testes internos.
    return round(min(1.0, max(0.05, contrast / 85.0)), 3)


def _resolve_thumbnail(export_folder: Path | None, result: dict | None) -> Path | None:
    if result:
        meta = result.get("youtube_metadata") or {}
        thumb = meta.get("thumbnail")
        if thumb and Path(str(thumb)).exists():
            return Path(str(thumb))
    if export_folder:
        candidate = export_folder / "thumbnail.jpg"
        if candidate.exists():
            return candidate
    return None


def _infer_tts_provider(result: dict | None) -> str:
    if not result:
        return "unknown"
    audio = result.get("audio")
    if not audio:
        return "unknown"
    meta = result.get("audio_metadata") or {}
    return meta.get("provider", "unknown")


def _resolve_template(result: dict | None) -> str:
    if not result:
        return "documentario"
    strategy = result.get("estrategia") or {}
    return strategy.get("template") or strategy.get("estilo_video") or "documentario"


def _total_duration(perf_report: dict | None) -> float | None:
    if not perf_report:
        return None
    timings = perf_report.get("step_timings") or {}
    if not timings:
        return perf_report.get("total_seconds")
    return round(sum(float(v) for v in timings.values()), 3)
