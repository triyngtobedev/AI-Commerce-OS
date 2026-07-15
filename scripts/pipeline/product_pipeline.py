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
from scripts.video.asset_search import generate_asset_queries

from scripts.video.media_search import search_media
from scripts.video.media_downloader import download_videos

from scripts.video.persona_media_pipeline import (
    generate_persona_media,
    should_use_persona,
)

from scripts.video.subtitle_generator import generate_subtitles
from scripts.video.renderer import render_video_project


from scripts.audio.tts_generator import create_audio


from database.database_manager import save_product

from scripts.publisher.exporter import export_product

from scripts.dashboard.generator import generate_dashboard

from scripts.core.pipeline_result import PipelineResult



def slugify(text):

    return (
        text
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
    )



def _run_media_pipeline(product, scenes, queries):
    """
    Decide e executa o pipeline de mídia correto.

    Modo PERSONA:
        Tenta gerar imagens com a influenciadora virtual.
        Só limpa assets antigos se a geração foi bem-sucedida.
        Faz fallback para stock se persona retornar 0 imagens.

    Modo STOCK:
        Busca e baixa mídia do Pexels diretamente.

    Retorna:
        "persona"  — usou persona com sucesso
        "stock"    — usou stock (direto ou via fallback)
    """

    if not should_use_persona():

        print(
            "📸 Modo STOCK ativado."
        )

        media = search_media(
            product,
            queries
        )

        download_videos(
            product,
            media
        )

        return "stock"


    # ================================
    # MODO PERSONA
    # ================================

    print(
        "🤖 Modo PERSONA ativado."
    )

    persona_images = generate_persona_media(
        product,
        scenes
    )

    if persona_images:

        # Persona gerou imagens — pipeline encerrado aqui.
        # clear_old_assets já foi chamado internamente
        # pelo generate_persona_media após confirmação.
        print(
            f"✅ Persona: {len(persona_images)} imagem(ns) gerada(s)."
        )

        return "persona"


    # ================================
    # FALLBACK: PERSONA → STOCK
    # ================================

    total_scenes = len(
        scenes.get("cenas", [])
    )

    print(
        f"⚠️ Persona falhou (0 de {total_scenes} cenas). "
        "Usando stock como fallback."
    )

    media = search_media(
        product,
        queries
    )

    download_videos(
        product,
        media
    )

    return "stock"



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
                    (
                        f"output/"
                        f"{slugify(product['nome'])}/"
                        f"assets/audio/narracao.mp3"
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



            generate_dashboard(
                results
            )



        except Exception as error:

            print(
                f"❌ Erro processando {product['nome']}: {error}"
            )

            continue



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