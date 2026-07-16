"""
Pipeline YouTube resumível para produção contínua.

Cada etapa persiste estado e artefatos. Falhas permitem retomada
da última etapa válida sem reprocessamento desnecessário.
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from scripts.core.pipeline_result import PipelineResult
from scripts.core.platform_config import YOUTUBE_DARK
from scripts.core.production.cleanup import cleanup_temp_files
from scripts.core.production.health_check import run_health_check
from scripts.core.production.quality_score import run_quality_score
from scripts.core.production.logger import get_logger
from scripts.core.production.manifest import generate_production_manifest
from scripts.core.production.monetization_audit import run_monetization_audit
from scripts.core.production.performance_audit import generate_performance_report
from scripts.core.production.pipeline_state import STAGE_ORDER, PipelineState
from scripts.core.production.stage_cache import StageCache
from scripts.utils.slug import content_output_dir

from scripts.youtube.topic_analyst import analyze_topic
from scripts.youtube.topic_scorer import calculate_topic_score
from scripts.youtube.topic_opportunity import analyze_topic_opportunity
from scripts.decision.decision_engine import decide_action
from scripts.youtube.youtube_strategy import generate_youtube_strategy
from scripts.youtube.youtube_script import generate_youtube_script
from scripts.youtube.youtube_content import generate_youtube_content
from scripts.youtube.youtube_scenes import generate_youtube_scenes
from scripts.youtube.chapter_builder import build_chapters
from scripts.youtube.thumbnail_generator import generate_thumbnail

from scripts.video.caption_generator import generate_caption
from scripts.video.asset_search import generate_asset_queries
from scripts.video.subtitle_generator import generate_subtitles
from scripts.video.project_builder import build_video_project
from scripts.video.renderer import render_video_project
from scripts.video.scene_timeline import sync_scenes_to_audio
from scripts.video.asset_manager import prepare_assets

from scripts.pipeline.shared_media import run_media_pipeline
from scripts.audio.tts_generator import create_audio
from scripts.audio.soundtrack_engine import generate_soundtrack

from scripts.publisher.youtube_exporter import export_youtube_video
from scripts.publisher.youtube_auth import is_upload_configured, validate_credentials
from scripts.publisher.youtube_publish_config import (
    resolve_upload_settings,
    resolve_upload_visibility,
)
from scripts.publisher.youtube_uploader import UPLOAD_STATUS, upload_from_folder
from scripts.metrics.metrics_tracker import record_production

from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.emotional_timeline import EmotionalTimeline
from scripts.core.timeline_sync import sync_timeline_to_audio
from scripts.core.visual_intent_engine import apply_visual_intents
from scripts.core.emotional_effects import apply_effect_hints_to_scenes


class StageContext:
    """Contexto compartilhado entre etapas do pipeline."""

    def __init__(self, topic: dict, output_dir: Path):
        self.topic = topic
        self.output_dir = output_dir
        self.state = PipelineState(output_dir)
        self.cache = StageCache(output_dir)
        self.data: Dict[str, Any] = {"topic": topic}
        self.providers_used: List[str] = []


def _serialize_timeline(timeline: EmotionalTimeline | dict | None) -> dict:
    if timeline is None:
        return {}
    if isinstance(timeline, EmotionalTimeline):
        return timeline.to_dict()
    return timeline


def _deserialize_timeline(timeline: EmotionalTimeline | dict | None) -> EmotionalTimeline | None:
    if timeline is None:
        return None
    if isinstance(timeline, EmotionalTimeline):
        return timeline
    if isinstance(timeline, dict):
        return EmotionalTimeline.from_dict(timeline)
    return None


def _timed_stage(ctx: StageContext, stage: str, fn: Callable[[], Any]) -> Any:
    logger = get_logger(stage)
    logger.stage_start()
    ctx.state.mark_started(stage)
    start = time.monotonic()

    try:
        result = fn()
        elapsed = time.monotonic() - start
        ctx.state.mark_completed(stage, elapsed)
        logger.stage_end(elapsed, success=True)
        return result
    except Exception as exc:
        elapsed = time.monotonic() - start
        ctx.state.mark_failed(stage, str(exc))
        logger.stage_end(elapsed, success=False)
        logger.error(f"Etapa '{stage}' falhou", error=str(exc))
        raise


def _stage_collect(ctx: StageContext) -> dict:
    topic = ctx.topic
    topic["_output_platform"] = YOUTUBE_DARK.id
    prepare_assets(topic)
    ctx.state.save_artifact("topic.json", topic)
    return topic


def _stage_analysis(ctx: StageContext) -> dict:
    topic = ctx.data["topic"]
    cache_input = {"nome": topic.get("nome"), "categoria": topic.get("categoria")}
    artifacts = [ctx.output_dir / "analysis.json"]

    if ctx.cache.is_valid("analysis", cache_input, artifacts):
        loaded = ctx.state.load_artifact("analysis.json")
        if loaded:
            ctx.data.update(loaded)
            return loaded

    score = calculate_topic_score(topic)
    analysis = analyze_topic(topic)
    opportunity = analyze_topic_opportunity(analysis, score)
    action = decide_action(opportunity)

    if action == "DESCARTAR":
        raise RuntimeError(
            f"Tema descartado (score: {opportunity.get('score_venda', 0)})"
        )

    payload = {
        "score": score,
        "analysis": analysis,
        "opportunity": opportunity,
        "action": action,
    }
    ctx.state.save_artifact("analysis.json", payload)
    ctx.data.update(payload)
    ctx.cache.record("analysis", cache_input, artifacts)
    return payload


def _stage_strategy(ctx: StageContext) -> dict:
    topic = ctx.data["topic"]
    cache_input = {
        "topic": topic.get("nome"),
        "analysis": ctx.data.get("analysis", {}),
    }
    artifacts = [ctx.output_dir / "strategy.json"]

    if ctx.cache.is_valid("strategy", cache_input, artifacts):
        loaded = ctx.state.load_artifact("strategy.json")
        if loaded:
            ctx.data["strategy"] = loaded
            return loaded

    strategy = generate_youtube_strategy(
        topic,
        ctx.data["analysis"],
        ctx.data["opportunity"],
    )
    ctx.state.save_artifact("strategy.json", strategy)
    ctx.data["strategy"] = strategy
    ctx.cache.record("strategy", cache_input, artifacts)
    return strategy


def _stage_script(ctx: StageContext) -> dict:
    topic = ctx.data["topic"]
    cache_input = {"topic": topic.get("nome"), "strategy": ctx.data.get("strategy")}
    artifacts = [ctx.output_dir / "script.json"]

    if ctx.cache.is_valid("script", cache_input, artifacts):
        loaded = ctx.state.load_artifact("script.json")
        if loaded:
            ctx.data["script"] = loaded
            return loaded

    script = generate_youtube_script(
        topic,
        ctx.data["analysis"],
        ctx.data["opportunity"],
        ctx.data["strategy"],
    )
    ctx.state.save_artifact("script.json", script)
    ctx.data["script"] = script
    ctx.cache.record("script", cache_input, artifacts)
    return script


def _stage_timeline(ctx: StageContext) -> dict:
    topic = ctx.data["topic"]
    cache_input = {"script_hash": str(hash(str(ctx.data.get("script"))))}
    artifacts = [ctx.output_dir / "scenes.json"]

    if ctx.cache.is_valid("timeline", cache_input, artifacts):
        loaded = ctx.state.load_artifact("scenes.json")
        if loaded:
            ctx.data["scenes"] = loaded
            emotional = ctx.state.load_artifact("emotional_timeline.json")
            if emotional:
                ctx.data["emotional_timeline"] = _deserialize_timeline(emotional)
            content = ctx.state.load_artifact("content.json")
            if content:
                ctx.data["content"] = content
            caption = ctx.state.load_artifact("caption.json")
            if caption:
                ctx.data["caption"] = caption
            queries = ctx.state.load_artifact("asset_queries.json")
            if queries:
                ctx.data["queries"] = queries
            return loaded

    content = generate_youtube_content(
        topic,
        ctx.data["analysis"],
        ctx.data["opportunity"],
        ctx.data["script"],
        ctx.data["strategy"],
    )

    if not content.get("texto_narracao"):
        raise RuntimeError("Conteúdo sem narração")

    caption = generate_caption(content)
    emotional_timeline = build_emotional_timeline(
        ctx.data["script"],
        director_meta=ctx.data["script"].get("_director"),
    )
    emotional_timeline = apply_visual_intents(emotional_timeline)

    scenes = generate_youtube_scenes(topic, content, ctx.data["strategy"])
    queries = generate_asset_queries(
        scenes,
        platform=YOUTUBE_DARK.id,
        timeline=emotional_timeline,
    )

    ctx.state.save_artifact("content.json", content)
    ctx.state.save_artifact("caption.json", caption)
    ctx.state.save_artifact("emotional_timeline.json", _serialize_timeline(emotional_timeline))
    ctx.state.save_artifact("scenes.json", scenes)
    ctx.state.save_artifact("asset_queries.json", queries)

    ctx.data.update({
        "content": content,
        "caption": caption,
        "emotional_timeline": emotional_timeline,
        "scenes": scenes,
        "queries": queries,
    })
    ctx.cache.record("timeline", cache_input, artifacts)
    return scenes


def _stage_media(ctx: StageContext) -> str:
    topic = ctx.data["topic"]
    cache_input = {"queries": ctx.data.get("queries")}
    media_marker = ctx.output_dir / "assets" / "media_search.json"
    artifacts = [media_marker] if media_marker.exists() else [ctx.output_dir / "assets"]

    if ctx.cache.is_valid("media", cache_input, [ctx.output_dir / "assets"]):
        mode = ctx.state.load_artifact("media_mode.json") or {"mode": "cached"}
        return mode.get("mode", "cached")

    mode = run_media_pipeline(topic, ctx.data["scenes"], ctx.data["queries"])
    ctx.state.save_artifact("media_mode.json", {"mode": mode})
    ctx.state.add_provider(mode)
    ctx.providers_used.append(mode)
    ctx.cache.record("media", cache_input, [ctx.output_dir / "assets"])
    return mode


def _stage_audio(ctx: StageContext) -> str:
    topic = ctx.data["topic"]
    audio_path = ctx.output_dir / "assets" / "audio" / "narracao.mp3"
    cache_input = {"narration_len": len(ctx.data["content"].get("texto_narracao", ""))}

    if ctx.cache.is_valid("audio", cache_input, [audio_path]):
        ctx.data["audio"] = str(audio_path)
        return str(audio_path)

    audio = create_audio({
        "text": ctx.data["content"]["texto_narracao"],
        "script_sections": ctx.data["script"],
        "emotional_timeline": ctx.data["emotional_timeline"],
        "output_path": str(audio_path),
        "narration_style": ctx.data["strategy"].get(
            "estilo_video",
            YOUTUBE_DARK.narration_style,
        ),
    })

    emotional_timeline = sync_timeline_to_audio(
        _deserialize_timeline(ctx.data["emotional_timeline"]),
        audio,
    )
    ctx.data["emotional_timeline"] = emotional_timeline
    ctx.state.save_artifact("emotional_timeline.json", _serialize_timeline(emotional_timeline))

    scenes = sync_scenes_to_audio(
        ctx.data["scenes"],
        ctx.data["content"]["texto_narracao"],
        audio,
        emotional_timeline=emotional_timeline,
        script=ctx.data["script"],
    )
    scenes = apply_effect_hints_to_scenes(scenes, emotional_timeline)
    ctx.data["scenes"] = scenes
    ctx.state.save_artifact("scenes.json", scenes)

    ctx.data["audio"] = audio
    ctx.cache.record("audio", cache_input, [Path(audio)])
    return audio


def _stage_render(ctx: StageContext) -> Optional[str]:
    topic = ctx.data["topic"]
    content = ctx.data["content"]
    video_path = ctx.output_dir / "video_final.mp4"

    cache_input = {"scenes_count": len(ctx.data["scenes"].get("cenas", []))}
    thumb_path = ctx.output_dir / "thumbnail.jpg"

    if ctx.cache.is_valid("render", cache_input, [video_path]):
        ctx.data["video"] = str(video_path)
        if thumb_path.exists():
            ctx.data["thumbnail"] = str(thumb_path)
        return str(video_path)

    soundtrack_path = ctx.output_dir / "assets" / "audio" / "soundtrack.mp3"
    cenas = ctx.data.get("scenes", {})
    audio_duration = float(cenas.get("audio_duration", 0)) if isinstance(cenas, dict) else 0
    soundtrack = generate_soundtrack(
        soundtrack_path,
        emotional_timeline=ctx.data.get("emotional_timeline"),
        audio_duration=audio_duration,
        narration_path=Path(ctx.data["audio"]) if ctx.data.get("audio") else None,
    )
    if soundtrack:
        ctx.data["soundtrack"] = str(soundtrack)

    subtitles = generate_subtitles({"produto": topic, "cenas": ctx.data["scenes"]})
    chapters = build_chapters(content, ctx.data["scenes"])

    pipeline_result = PipelineResult(
        produto=topic,
        analise=ctx.data["analysis"],
        oportunidade=ctx.data["opportunity"],
        acao=ctx.data["action"],
        estrategia=ctx.data["strategy"],
        roteiro=ctx.data["script"],
        conteudo=content,
        legenda=ctx.data["caption"],
        cenas=ctx.data["scenes"],
        asset_queries=ctx.data["queries"],
        audio=ctx.data["audio"],
        subtitle_file=str(subtitles) if subtitles else None,
        platform=YOUTUBE_DARK.id,
        youtube_metadata={
            "capitulos": chapters,
            "tags": content.get("tags", []),
            "categoria": content.get("categoria_youtube", "Education"),
        },
    )

    errors = pipeline_result.validate()
    if errors:
        raise RuntimeError(f"Resultado inválido: {errors}")

    result = pipeline_result.to_dict()
    result["emotional_timeline"] = _serialize_timeline(ctx.data.get("emotional_timeline"))
    if ctx.data.get("soundtrack"):
        result["soundtrack"] = ctx.data["soundtrack"]
    if isinstance(result.get("cenas"), dict):
        result["cenas"]["emotional_timeline"] = _serialize_timeline(ctx.data.get("emotional_timeline"))
    build_video_project(result)
    video = render_video_project(result)

    if not video:
        raise RuntimeError("Vídeo não criado")

    pipeline_result.video = str(video)
    thumbnail = generate_thumbnail(
        topic,
        content,
        video_path=pipeline_result.video,
        platform=YOUTUBE_DARK.id,
        scenes=ctx.data["scenes"],
        strategy=ctx.data["strategy"],
    )

    if thumbnail:
        pipeline_result.youtube_metadata["thumbnail"] = thumbnail
        ctx.data["thumbnail"] = thumbnail

    ctx.data["pipeline_result"] = pipeline_result
    ctx.data["subtitles"] = subtitles
    ctx.data["chapters"] = chapters
    ctx.data["video"] = str(video)

    output_files = [Path(video)]
    if thumbnail:
        output_files.append(Path(thumbnail))
    ctx.cache.record("render", cache_input, output_files)
    return str(video)


def _stage_export(ctx: StageContext) -> Path:
    pr = ctx.data.get("pipeline_result")
    if not pr:
        raise RuntimeError("PipelineResult ausente — execute render primeiro")

    result = pr.to_dict()
    folder = export_youtube_video(result)
    ctx.data["export_folder"] = folder
    return folder


def _stage_validate(ctx: StageContext, *, block_upload: bool = True) -> dict:
    pr = ctx.data["pipeline_result"]
    folder = ctx.data["export_folder"]
    report = run_health_check(folder, pr.to_dict())

    ctx.data["health_report"] = report
    if block_upload and not report.valid:
        raise RuntimeError(
            f"Health check reprovado: {'; '.join(report.errors[:5])}"
        )

    quality = run_quality_score(folder, pr.to_dict())
    ctx.data["quality_report"] = quality

    if block_upload and not quality.passed:
        raise RuntimeError(
            f"Quality Score reprovado ({quality.score}/100): "
            f"{'; '.join(quality.failures[:5])}"
        )

    return {
        "health": report.to_dict(),
        "quality": quality.to_dict(),
    }


def _stage_upload(
    ctx: StageContext,
    *,
    should_upload: bool,
    privacy_status: str,
    upload_context: dict,
) -> dict:
    folder = ctx.data["export_folder"]

    if not should_upload:
        return {
            "status": UPLOAD_STATUS["skipped"],
            "message": upload_context.get("reason", "Upload desabilitado"),
        }

    if not is_upload_configured():
        auth_status = validate_credentials()
        return {
            "status": UPLOAD_STATUS["failed"],
            "message": "Credenciais não configuradas",
            "missing": auth_status.missing,
        }

    return upload_from_folder(folder, privacy_status=privacy_status)


def _stage_manifest(ctx: StageContext, upload_result: dict, perf_report: dict) -> Path:
    pr = ctx.data["pipeline_result"]
    folder = ctx.data["export_folder"]
    return generate_production_manifest(
        folder,
        pr.to_dict(),
        pipeline_state=ctx.state.to_dict(),
        upload_result=upload_result,
        providers_used=ctx.providers_used,
        performance_report=perf_report,
    )


def _stage_report(ctx: StageContext) -> dict:
    folder = ctx.data["export_folder"]
    perf = generate_performance_report(folder, ctx.state.to_dict())
    monetization = run_monetization_audit(
        ctx.data["pipeline_result"].to_dict(),
        folder,
    )
    cleanup_temp_files(folder)
    ctx.state.mark_finished()
    return {"performance": perf, "monetization": monetization}


STAGE_RUNNERS = {
    "collect": lambda ctx, **kw: _stage_collect(ctx),
    "analysis": lambda ctx, **kw: _stage_analysis(ctx),
    "strategy": lambda ctx, **kw: _stage_strategy(ctx),
    "script": lambda ctx, **kw: _stage_script(ctx),
    "timeline": lambda ctx, **kw: _stage_timeline(ctx),
    "media": lambda ctx, **kw: _stage_media(ctx),
    "audio": lambda ctx, **kw: _stage_audio(ctx),
    "render": lambda ctx, **kw: _stage_render(ctx),
    "export": lambda ctx, **kw: _stage_export(ctx),
    "validate": lambda ctx, **kw: _stage_validate(ctx, block_upload=kw.get("block_upload", True)),
    "upload": lambda ctx, **kw: _stage_upload(
        ctx,
        should_upload=kw.get("should_upload", False),
        privacy_status=kw.get("privacy_status", "private"),
        upload_context=kw.get("upload_context", {}),
    ),
    "manifest": lambda ctx, **kw: _stage_manifest(ctx, kw["upload_result"], kw["perf_report"]),
    "report": lambda ctx, **kw: _stage_report(ctx),
}


def run_resumable_youtube_pipeline(
    topic: dict,
    *,
    production_mode: bool = False,
    auto_upload: bool = False,
    privacy_status: str = "private",
    force_restart: bool = False,
    force: bool = False,
) -> Optional[dict]:
    """
    Executa pipeline resumível para um tema YouTube.

    Retorna resultado serializado ou None em caso de falha/descarte.
    """

    main_logger = get_logger("pipeline")
    topic["_output_platform"] = YOUTUBE_DARK.id
    output_dir = content_output_dir(topic, platform=YOUTUBE_DARK.id)
    output_dir.mkdir(parents=True, exist_ok=True)

    ctx = StageContext(topic, output_dir)

    if force_restart or force:
        ctx.state = PipelineState(output_dir)
        ctx.state._data = ctx.state._load()
        ctx.state._data["completed_steps"] = []
        ctx.state.save()

        had_stage_cache = bool(ctx.cache._data.get("stages"))
        ctx.cache.invalidate_from("collect", STAGE_ORDER)
        main_logger.info(
            f"Reprocessando tema existente: {topic.get('nome', '')} "
            f"— output: {output_dir}, "
            f"stage cache invalidado: {'sim' if had_stage_cache else 'não'}"
        )

    should_upload, upload_context = resolve_upload_settings(cli_upload=auto_upload)

    if production_mode:
        should_upload = True
        privacy_status, vis_ctx = resolve_upload_visibility(cli_privacy=privacy_status)
        main_logger.info(
            f"Modo produção ativo — visibilidade: {privacy_status} "
            f"({vis_ctx['reason']})"
        )

    resume_from = ctx.state.get_resume_stage()
    if resume_from:
        main_logger.info(f"Retomando pipeline a partir da etapa: {resume_from}")

    upload_result = {"status": UPLOAD_STATUS["skipped"]}
    perf_report: dict = {}

    try:
        for stage in STAGE_ORDER:
            if ctx.state.should_skip(stage):
                main_logger.info(f"Etapa '{stage}' já concluída — pulando")
                _restore_stage_data(ctx, stage)
                continue

            if stage == "upload":
                upload_result = _timed_stage(
                    ctx,
                    stage,
                    lambda: _stage_upload(
                        ctx,
                        should_upload=should_upload,
                        privacy_status=privacy_status,
                        upload_context=upload_context,
                    ),
                )
                continue

            if stage == "manifest":
                perf_report = generate_performance_report(output_dir, ctx.state.to_dict())
                _timed_stage(
                    ctx,
                    stage,
                    lambda: _stage_manifest(ctx, upload_result, perf_report),
                )
                continue

            if stage == "report":
                _timed_stage(ctx, stage, lambda: _stage_report(ctx))
                continue

            runner = STAGE_RUNNERS.get(stage)
            if runner:
                _timed_stage(ctx, stage, lambda r=runner: r(ctx, block_upload=True))

        result = ctx.data["pipeline_result"].to_dict()
        record_production(
            result,
            upload_result=upload_result,
            update_existing=force,
        )

        main_logger.success(f"Pipeline concluído: {topic.get('nome')}")
        return result

    except Exception as exc:
        main_logger.error(
            f"Pipeline interrompido em '{ctx.state._data.get('current_step')}'",
            error=str(exc),
        )
        if production_mode:
            main_logger.error(traceback.format_exc())
        return None


def _restore_stage_data(ctx: StageContext, stage: str):
    """Restaura dados do contexto a partir de artefatos salvos."""

    artifacts_map = {
        "analysis": ["analysis"],
        "strategy": ["strategy"],
        "script": ["script"],
        "timeline": ["content", "caption", "scenes", "queries", "emotional_timeline"],
        "audio": ["audio"],
        "render": ["pipeline_result"],
        "export": ["export_folder"],
    }

    file_map = {
        "analysis": "analysis.json",
        "strategy": "strategy.json",
        "script": "script.json",
        "content": "content.json",
        "caption": "caption.json",
        "scenes": "scenes.json",
        "queries": "asset_queries.json",
        "emotional_timeline": "emotional_timeline.json",
    }

    for key in artifacts_map.get(stage, []):
        filename = file_map.get(key, f"{key}.json")
        data = ctx.state.load_artifact(filename)
        if data is None:
            continue

        if key == "analysis" and isinstance(data, dict):
            ctx.data.update(data)
        elif key == "queries":
            ctx.data["queries"] = data
        else:
            ctx.data[key] = data

    if stage in ("render", "export", "validate", "upload", "manifest", "report"):
        _rebuild_pipeline_result(ctx)


def _rebuild_pipeline_result(ctx: StageContext):
    """Reconstrói PipelineResult a partir de artefatos."""

    if "pipeline_result" in ctx.data:
        return

    required = ("topic", "analysis", "opportunity", "action", "strategy", "script", "content")
    if not all(k in ctx.data for k in required):
        return

    pr = PipelineResult(
        produto=ctx.data["topic"],
        analise=ctx.data.get("analysis", {}),
        oportunidade=ctx.data.get("opportunity", {}),
        acao=ctx.data.get("action", "avaliar"),
        estrategia=ctx.data.get("strategy", {}),
        roteiro=ctx.data.get("script", {}),
        conteudo=ctx.data.get("content", {}),
        legenda=ctx.data.get("caption", {}),
        cenas=ctx.data.get("scenes", {}),
        asset_queries=ctx.data.get("queries", []),
        audio=ctx.data.get("audio"),
        platform=YOUTUBE_DARK.id,
    )

    video = ctx.output_dir / "video_final.mp4"
    if video.exists():
        pr.video = str(video)

    thumb = ctx.data.get("thumbnail")
    if thumb:
        pr.youtube_metadata["thumbnail"] = thumb

    ctx.data["pipeline_result"] = pr

    export_folder = ctx.output_dir
    if (export_folder / "post_package.json").exists():
        ctx.data["export_folder"] = export_folder
