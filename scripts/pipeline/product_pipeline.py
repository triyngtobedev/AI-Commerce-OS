from scripts.content.content_generator import generate_content
from scripts.creative.ai_script_generator import generate_ai_script
from scripts.creative.creative_strategy_engine import generate_creative_strategy

from scripts.data_sources.tiktok.collector import collect_products

from scripts.ai.analysts.ai_analyst import analyze_product

from scripts.affiliate.opportunity_engine import analyze_opportunity

from scripts.scoring.product_score import calculate_product_score
from scripts.scoring.product_ranker import rank_products

from scripts.decision.decision_engine import decide_action


from scripts.video.scene_generator import generate_scenes
from scripts.video.caption_generator import generate_caption
from scripts.video.project_builder import build_video_project

from scripts.video.asset_manager import prepare_assets
from scripts.pipeline.shared_media import run_media_pipeline as _run_media_pipeline

from scripts.video.subtitle_generator import generate_subtitles
from scripts.video.renderer import render_video_project


from scripts.audio.tts_generator import create_audio


from database.database_manager import save_product

from scripts.publisher.exporter import export_product

from scripts.dashboard.generator import generate_dashboard

from scripts.core.pipeline_result import PipelineResult
from scripts.utils.slug import slugify, product_output_dir



def run_pipeline():

    print(
        "🚀 Pipeline iniciado\n"
    )


    products = collect_products()


    if not products:

        print(
            "❌ Nenhum produto encontrado"
        )

        return []



    for product in products:

        product["score_tecnico"] = (
            calculate_product_score(product)
        )



    ranked = rank_products(
        products
    )



    selected = [
        item["produto"]
        for item in ranked[:3]
    ]



    results = []



    for product in selected:

        try:

            print(
                "\n============================"
            )

            print(
                f"Produto: {product['nome']}"
            )


            prepare_assets(
                product
            )


            score = calculate_product_score(
                product
            )


            analysis = analyze_product(
                product
            )


            opportunity = analyze_opportunity(
                analysis,
                score
            )


            action = decide_action(
                opportunity
            )


            if action == "DESCARTAR":

                print(
                    f"⏭️ Produto descartado "
                    f"(score: {opportunity.get('score_venda', 0)})."
                )

                continue


            print(
                f"▶️ Ação: {action} "
                f"(score: {opportunity.get('score_venda', 0)})"
            )


            creative_strategy = generate_creative_strategy(
                product,
                analysis,
                opportunity
            )


            script = generate_ai_script(
                product,
                analysis,
                opportunity,
                creative_strategy
            )


            content = generate_content(
                product,
                analysis,
                opportunity,
                script,
                creative_strategy
            )


            if not content.get(
                "texto_narracao"
            ):

                print(
                    "⚠️ Conteúdo sem narração."
                )

                continue



            caption = generate_caption(
                content
            )


            scenes = generate_scenes(
                product,
                content,
                creative_strategy
            )


            queries = generate_asset_queries(
                scenes
            )


            subtitles = generate_subtitles(
                {
                    "produto": product,
                    "cenas": scenes
                }
            )


            # ================================
            # PIPELINE DE MÍDIA
            # ================================
            # Isolado em _run_media_pipeline para
            # deixar o fluxo principal limpo e
            # garantir que o fallback funcione
            # sem efeitos colaterais nos assets.

            _run_media_pipeline(
                product,
                scenes,
                queries
            )


            audio = create_audio(
                {
                    "text":
                        content["texto_narracao"],

                    "output_path":
                    str(
                        product_output_dir(product)
                        / "assets"
                        / "audio"
                        / "narracao.mp3"
                    )
                }
            )



            pipeline_result = PipelineResult(

                produto=product,

                analise=analysis,

                oportunidade=opportunity,

                acao=action,

                estrategia=creative_strategy,

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
                )

            )



            errors = pipeline_result.validate()


            if errors:

                print(
                    f"❌ Resultado inválido: {errors}"
                )

                continue



            result = pipeline_result.to_dict()



            build_video_project(
                result
            )



            video = render_video_project(
                result
            )



            if video:

                pipeline_result.video = (
                    str(video)
                )


                print(
                    f"✅ Vídeo criado: {video}"
                )


            else:

                print(
                    "⚠️ Vídeo não criado."
                )



            result = pipeline_result.to_dict()



            save_product(
                result
            )



            export_product(
                result
            )



            results.append(
                result
            )


        except Exception as error:

            print(
                f"❌ Erro processando {product['nome']}: {error}"
            )

            continue


    if results:

        generate_dashboard(
            results
        )


    print(
        "\n=============================="
    )

    print(
        "PROCESSO FINALIZADO"
    )

    print(
        f"Vídeos gerados: {len(results)}"
    )

    print(
        "=============================="
    )


    return results