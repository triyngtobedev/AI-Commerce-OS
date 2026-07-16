"""
Pipeline YouTube Dark

Orquestra produção de vídeos documentários para YouTube,
reutilizando engines compartilhados de mídia, áudio e render.
"""

import os

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

from scripts.video.caption_generator import generate_caption
from scripts.video.asset_search import generate_asset_queries
from scripts.video.subtitle_generator import generate_subtitles
from scripts.video.project_builder import build_video_project
from scripts.video.renderer import render_video_project
from scripts.video.scene_timeline import sync_scenes_to_audio
from scripts.video.asset_manager import prepare_assets

from scripts.pipeline.shared_media import run_media_pipeline
from scripts.audio.tts_generator import create_audio

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

from scripts.core.emotional_timeline import build_emotional_timeline
from scripts.core.timeline_sync import sync_timeline_to_audio
from scripts.core.visual_intent_engine import apply_visual_intents
from scripts.core.emotional_effects import apply_effect_hints_to_scenes
from scripts.utils.slug import content_output_dir


def run_youtube_pipeline(
    auto_research: bool = False,
    research_count: int = 3,
    max_videos: int = 1,
    auto_upload: bool = False,
    privacy_status: str = "private",
    force_topic_name: str = None,
    production_mode: bool = False,
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


    processed_names = collect_processed_topic_names(
        platform=YOUTUBE_DARK.id,
    )


    selected = select_next_topics(
        topics,
        max_videos=max_videos,
        platform=YOUTUBE_DARK.id,
        force_topic_name=force_topic_name,
        processed_names=processed_names,
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


            script = generate_youtube_script(
                topic,
                analysis,
                opportunity,
                strategy,
            )


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


            output_dir = content_output_dir(
                topic,
                platform=YOUTUBE_DARK.id,
            )


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


            build_video_project(result)


            video = render_video_project(result)


            if video:

                pipeline_result.video = str(video)

                print(
                    f"✅ Vídeo criado: {video}"
                )

            else:

                print(
                    "⚠️ Vídeo não criado."
                )


            thumbnail = generate_thumbnail(
                topic,
                content,
                video_path=pipeline_result.video,
                platform=YOUTUBE_DARK.id,
                scenes=scenes,
                strategy=strategy,
            )


            if thumbnail:

                pipeline_result.youtube_metadata[
                    "thumbnail"
                ] = thumbnail

            else:

                print(
                    "⚠️ Thumbnail não gerada — "
                    "post_package será exportado sem capa customizada"
                )


            result = pipeline_result.to_dict()


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
