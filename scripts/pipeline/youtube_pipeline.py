"""
Pipeline YouTube Dark

Orquestra produção de vídeos documentários para YouTube,
reutilizando engines compartilhados de mídia, áudio e render.
"""

import os
from pathlib import Path

from scripts.core.pipeline_result import PipelineResult
from scripts.core.platform_config import YOUTUBE_DARK
from scripts.core.content_subject import normalize_subject

from scripts.data_sources.youtube.topic_collector import collect_topics
from scripts.research.topic_research_engine import research_topics

from scripts.youtube.topic_analyst import analyze_topic
from scripts.youtube.topic_scorer import calculate_topic_score
from scripts.youtube.topic_selector import (
    collect_processed_topic_names,
    resolve_topic_for_production,
    select_next_topics,
)
from scripts.youtube.topic_opportunity import analyze_topic_opportunity
from scripts.decision.decision_engine import decide_action

from scripts.youtube.youtube_strategy import generate_youtube_strategy
from scripts.youtube.youtube_script import generate_youtube_script
from scripts.youtube.youtube_content import generate_youtube_content
from scripts.youtube.youtube_scenes import generate_youtube_scenes
from scripts.youtube.chapter_builder import build_chapters
from scripts.youtube.thumbnail_generator import generate_thumbnail
from scripts.youtube.thumbnail_variations import generate_thumbnail_variations

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
from scripts.audio.audio_layer import (
    build_sfx_timeline,
    generate_act_soundtrack,
    mix_final_audio,
)
from scripts.youtube.retention_controller import run_retention_controller
from scripts.youtube.lofi_dark_config import is_lofi_dark
from scripts.youtube.template_override import apply_template_override, get_template_override

from scripts.publisher.youtube_exporter import export_youtube_video
from scripts.publisher.youtube_auth import (
    is_upload_configured,
    validate_credentials,
)
from scripts.publisher.youtube_publish_config import (
    resolve_upload_settings,
)
from scripts.publisher.youtube_uploader import (
    UPLOAD_STATUS,
    upload_from_folder,
)
from scripts.metrics.metrics_tracker import record_production

from scripts.research.research_pack import generate_research_pack, validate_claims_against_pack
from scripts.youtube.retention_analyzer import run_retention_pipeline
from scripts.youtube.scene_visual_planner import enrich_scenes_with_visual_plan
from scripts.video.visual_grammar import apply_visual_grammar_to_scenes
from scripts.core.production.quality_gate import run_quality_gate
from scripts.core.asset_rights_ledger import AssetRightsLedger
from scripts.youtube.youtube_packager import generate_youtube_package

from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.timeline_sync import sync_timeline_to_audio
from scripts.core.visual_intent_engine import apply_visual_intents
from scripts.core.emotional_effects import apply_effect_hints_to_scenes
from scripts.utils.slug import content_output_dir


def _is_cloud_injected_topic() -> bool:
    """Tema explícito via API/n8n — não descartar por score baixo."""

    return bool(os.getenv("PIPELINE_TOPIC_OVERRIDE", "").strip())


def run_youtube_pipeline(
    auto_research: bool = False,
    research_count: int = 3,
    max_videos: int = 1,
    auto_upload: bool = False,
    privacy_status: str = "private",
    force_topic_name: str = None,
    production_mode: bool = False,
    force: bool = False,
):
    """
    Executa pipeline completo para YouTube Dark.

    Args:
        auto_research: Se True, pesquisa temas via IA antes de produzir
        research_count: Quantidade de temas a pesquisar
        max_videos: Máximo de vídeos a produzir por execução
        auto_upload: Se True, tenta publicar no YouTube
        privacy_status: Status de privacidade do upload

    Returns:
        Lista de resultados produzidos
    """

    print(
        "\n🎬 Pipeline YouTube Dark iniciado\n"
    )

    template_override = get_template_override()
    if template_override:
        print(f"📋 Template de roteiro: {template_override}\n")

    should_upload, upload_context = resolve_upload_settings(
        cli_upload=auto_upload or production_mode,
    )

    if production_mode:
        from scripts.core.production.logger import get_logger
        get_logger("pipeline").info(
            "Modo produção — pipeline automático sem confirmações"
        )

    print(
        f"📡 Publicação: {upload_context['decision'].upper()}"
    )
    print(
        f"   Motivo: {upload_context['reason']}"
    )

    if should_upload:
        if is_upload_configured():
            print(
                "   Credenciais: configuradas ✅"
            )
        else:
            print(
                "   Credenciais: NÃO configuradas ⚠️"
            )
    print()


    if auto_research:

        research_topics(
            niche="historia_curiosidades",
            count=research_count,
        )


    topics = collect_topics()


    if not topics:

        print(
            "❌ Nenhum tema encontrado"
        )

        return []


    if force:
        print(
            "⚡ Modo FORCE ativo — histórico de processamento ignorado\n"
        )

    processed_names = collect_processed_topic_names(
        platform=YOUTUBE_DARK.id,
    )


    selected = select_next_topics(
        topics,
        max_videos=max_videos,
        platform=YOUTUBE_DARK.id,
        force_topic_name=force_topic_name,
        processed_names=processed_names,
        force=force,
    )

    if not selected:

        print(
            "❌ Nenhum tema novo para produzir"
        )

        return []


    results = []


    for topic in selected:

        try:

            topic = resolve_topic_for_production(
                topic,
                topics,
                processed_names=processed_names,
                platform=YOUTUBE_DARK.id,
                force=force,
            )

            if not topic:

                continue

            if production_mode:
                from scripts.core.production.resumable_pipeline import (
                    run_resumable_youtube_pipeline,
                )

                topic["_output_platform"] = YOUTUBE_DARK.id
                result = run_resumable_youtube_pipeline(
                    topic,
                    production_mode=True,
                    auto_upload=should_upload,
                    privacy_status=privacy_status,
                    force=force,
                )

                if result:
                    processed_names.add(topic["nome"].strip().casefold())
                    processed_names.add(
                        content_output_dir(topic, platform=YOUTUBE_DARK.id).name
                    )
                    results.append(result)

                continue

            print(
                "\n============================"
            )

            print(
                f"Tema: {topic['nome']}"
            )


            prepare_assets(topic)


            score = calculate_topic_score(topic)

            analysis = analyze_topic(topic)

            opportunity = analyze_topic_opportunity(
                analysis,
                score,
            )

            action = decide_action(opportunity)

            if action == "DESCARTAR":
                if _is_cloud_injected_topic():
                    print(
                        f"⚡ Tema injetado pela API — "
                        f"ignorando score baixo ({opportunity.get('score_venda', 0)})"
                    )
                    action = "TESTAR_VIDEO"
                else:
                    print(
                        f"⏭️ Tema descartado "
                        f"(score: {opportunity.get('score_venda', 0)})."
                    )
                    continue

            print(
                f"▶️ Ação: {action} "
                f"(score: {opportunity.get('score_venda', 0)})"
            )


            strategy = generate_youtube_strategy(
                topic,
                analysis,
                opportunity,
            )
            strategy = apply_template_override(strategy)

            output_dir = content_output_dir(
                topic,
                platform=YOUTUBE_DARK.id,
            )

            research_pack = generate_research_pack(
                topic,
                analysis=analysis,
                output_dir=output_dir,
            )


            script = generate_youtube_script(
                topic,
                analysis,
                opportunity,
                strategy,
            )

            script, retention_report = run_retention_pipeline(
                script,
                topic=topic.get("nome", ""),
                output_dir=output_dir,
            )

            claims_check = validate_claims_against_pack(script, research_pack)
            if not claims_check.get("safe_to_proceed"):
                print(f"⚠️ Claims sensíveis sem fonte: {claims_check.get('flagged_claims', [])}")


            content = generate_youtube_content(
                topic,
                analysis,
                opportunity,
                script,
                strategy,
            )


            if not content.get("texto_narracao"):

                print(
                    "⚠️ Conteúdo sem narração."
                )

                continue


            caption = generate_caption(content)


            emotional_timeline = build_emotional_timeline(
                script,
                director_meta=script.get("_director"),
            )
            emotional_timeline = apply_visual_intents(emotional_timeline)


            scenes = generate_youtube_scenes(
                topic,
                content,
                strategy,
            )

            scenes = enrich_scenes_with_visual_plan(
                scenes,
                topic=topic.get("nome", ""),
                research_pack=research_pack,
                script=script,
            )
            scenes = apply_visual_grammar_to_scenes(scenes)


            audio = create_audio({
                "text": content["texto_narracao"],
                "script_sections": script,
                "emotional_timeline": emotional_timeline,
                "output_path": str(
                    output_dir
                    / "assets"
                    / "audio"
                    / "narracao.mp3"
                ),
                "narration_style": strategy.get(
                    "estilo_video",
                    YOUTUBE_DARK.narration_style,
                ),
            })


            emotional_timeline = sync_timeline_to_audio(
                emotional_timeline,
                audio,
            )


            scenes = sync_scenes_to_audio(
                scenes,
                content["texto_narracao"],
                audio,
                emotional_timeline=emotional_timeline,
                script=script,
            )

            scenes = apply_effect_hints_to_scenes(scenes, emotional_timeline)

            scenes, _retention_actions = run_retention_controller(
                scenes,
                retention_report=retention_report,
                script=script,
                output_dir=output_dir,
            )


            queries = generate_asset_queries(
                scenes,
                platform=YOUTUBE_DARK.id,
                timeline=emotional_timeline,
            )


            run_media_pipeline(
                topic,
                scenes,
                queries,
            )

            lofi_template = is_lofi_dark(strategy.get("roteiro_template"))

            if lofi_template:
                print("🌙 Lofi Dark: legendas opcionais — pulando geração automática.")
                subtitles = None
            else:
                subtitles = generate_subtitles({
                    "produto": topic,
                    "cenas": scenes,
                })


            chapters = build_chapters(
                content,
                scenes,
            )


            pipeline_result = PipelineResult(
                produto=topic,
                analise=analysis,
                oportunidade=opportunity,
                acao=action,
                estrategia=strategy,
                roteiro=script,
                conteudo=content,
                legenda=caption,
                cenas=scenes,
                asset_queries=queries,
                audio=audio,
                subtitle_file=(
                    str(subtitles)
                    if subtitles
                    else None
                ),
                platform=YOUTUBE_DARK.id,
                youtube_metadata={
                    "capitulos": chapters,
                    "tags": content.get("tags", []),
                    "categoria": content.get(
                        "categoria_youtube",
                        "Education",
                    ),
                },
            )


            errors = pipeline_result.validate()


            if errors:

                print(
                    f"❌ Resultado inválido: {errors}"
                )

                continue


            result = pipeline_result.to_dict()

            soundtrack_path = output_dir / "assets" / "audio" / "soundtrack.mp3"
            soundtrack = generate_act_soundtrack(
                output_dir,
                topic=topic.get("nome", ""),
                emotional_timeline=emotional_timeline,
                audio_duration=float(scenes.get("audio_duration", 0) or 0),
                roteiro_template=strategy.get("roteiro_template", ""),
            )
            if not soundtrack:
                soundtrack = generate_soundtrack(
                    soundtrack_path,
                    emotional_timeline=emotional_timeline,
                    audio_duration=float(scenes.get("audio_duration", 0) or 0),
                    narration_path=Path(audio) if audio else None,
                    roteiro_template=strategy.get("roteiro_template", ""),
                )
            if soundtrack:
                result["soundtrack"] = str(soundtrack)

            sfx_events = build_sfx_timeline(scenes, script=script)
            final_audio_path = output_dir / "assets" / "audio" / "final_audio.mp3"
            mixed = mix_final_audio(
                Path(audio) if audio else Path(""),
                final_audio_path,
                soundtrack_path=Path(soundtrack) if soundtrack else None,
                sfx_events=sfx_events,
                duration=float(scenes.get("audio_duration", 0) or 0),
            )
            if mixed and mixed != Path(audio):
                result["audio"] = str(mixed)
                result["audio_layer"] = {
                    "sfx_events": len(sfx_events),
                    "ducking": "sidechaincompress",
                    "soundtrack": str(soundtrack) if soundtrack else None,
                }
                result.pop("soundtrack", None)

            build_video_project(result)

            # Quality Gate pré-render
            ledger = AssetRightsLedger(output_dir)
            quality_gate = run_quality_gate(
                output_dir,
                result,
                block_on_failure=False,
                ledger=ledger,
            )
            if quality_gate.blocked:
                print(f"⚠️ Quality Gate: {'; '.join(quality_gate.block_reasons[:3])}")
            else:
                print(f"✅ Quality Gate: aprovado ({quality_gate.publish_ready_score}/100)")

            video = render_video_project(result)


            if not video:
                print("❌ Vídeo não criado — etapa de render falhou.")
                continue

            pipeline_result.video = str(video)
            print(f"✅ Vídeo criado: {video}")

            thumb_report = generate_thumbnail_variations(
                output_dir,
                subject=topic,
                content=content,
                strategy=strategy,
                scenes=scenes,
                video_path=pipeline_result.video,
                platform=YOUTUBE_DARK.id,
            )
            if thumb_report.get("final_thumbnail"):
                pipeline_result.youtube_metadata["thumbnail"] = thumb_report["final_thumbnail"]
                pipeline_result.youtube_metadata["thumbnail_ab"] = {
                    "winner": thumb_report.get("winner", {}).get("variant"),
                    "ctr_estimate": thumb_report.get("winner", {})
                    .get("scores", {})
                    .get("ctr_estimate"),
                }
            elif not pipeline_result.youtube_metadata.get("thumbnail"):
                thumbnail = generate_thumbnail(
                    topic,
                    content,
                    video_path=pipeline_result.video,
                    platform=YOUTUBE_DARK.id,
                    scenes=scenes,
                    strategy=strategy,
                )
                if thumbnail:
                    pipeline_result.youtube_metadata["thumbnail"] = thumbnail
                else:
                    print(
                        "⚠️ Thumbnail não gerada — "
                        "post_package será exportado sem capa customizada"
                    )

            result = pipeline_result.to_dict()
            generate_youtube_package(result, export_folder=output_dir)

            export_folder = export_youtube_video(result)

            upload_result = None

            if should_upload and is_upload_configured():

                print(
                    "\n📤 Iniciando publicação no YouTube..."
                )
                print(
                    f"   Pasta: {export_folder}"
                )

                upload_result = upload_from_folder(
                    export_folder,
                    privacy_status=privacy_status,
                )

                if upload_result.get("status") == "UPLOADED":
                    print(
                        f"\n🎉 Publicação concluída!"
                    )
                    print(
                        f"   Video ID: "
                        f"{upload_result.get('video_id')}"
                    )
                    print(
                        f"   URL: {upload_result.get('url')}"
                    )
                else:
                    print(
                        f"\n⚠️ Publicação não concluída: "
                        f"{upload_result.get('message', 'erro')}"
                    )

            elif should_upload:

                auth_status = validate_credentials()

                print(
                    "\n⚠️ Upload solicitado "
                    "mas credenciais não configuradas."
                )

                for message in auth_status.messages:
                    print(f"   {message}")

                print(
                    "   Configure com: python main.py --youtube-auth"
                )

                upload_result = {
                    "status": UPLOAD_STATUS["failed"],
                    "message": "Credenciais não configuradas",
                    "missing": auth_status.missing,
                }

            else:

                upload_result = {
                    "status": UPLOAD_STATUS["skipped"],
                    "message": upload_context["reason"],
                }

                print(
                    f"\n⏭️ Upload ignorado: "
                    f"{upload_context['reason']}"
                )

            record_production(
                result,
                upload_result=upload_result,
                update_existing=force,
            )

            processed_names.add(
                topic["nome"].strip().casefold()
            )
            processed_names.add(
                content_output_dir(
                    topic,
                    platform=YOUTUBE_DARK.id,
                ).name
            )


            results.append(result)


        except Exception as error:

            print(
                f"❌ Erro processando {topic['nome']}: {error}"
            )

            continue


    print(
        "\n=============================="
    )

    print(
        "PIPELINE YOUTUBE FINALIZADO"
    )

    print(
        f"Vídeos gerados: {len(results)}"
    )

    print(
        "=============================="
    )


    return results
