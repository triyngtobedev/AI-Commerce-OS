from scripts.content.content_generator import generate_content
from scripts.creative.ai_script_generator import generate_ai_script
from scripts.data_sources.tiktok.collector import collect_products
from scripts.ai.analysts.ai_analyst import analyze_product
from scripts.affiliate.opportunity_engine import analyze_opportunity
from database.database_manager import save_product
from scripts.publisher.exporter import export_product
from scripts.video.scene_generator import generate_scenes
from scripts.video.media_manager import prepare_media_folder
from scripts.scoring.product_score import calculate_product_score
from scripts.scoring.product_ranker import rank_products
from scripts.decision.decision_engine import decide_action
from scripts.dashboard.generator import generate_dashboard
from scripts.video.caption_generator import generate_caption
from scripts.video.project_builder import build_video_project
from scripts.video.renderer import render_video_project
from scripts.video.asset_manager import prepare_assets
from scripts.video.asset_search import generate_asset_queries
from scripts.video.media_search import search_media
from scripts.video.media_downloader import download_videos
from scripts.video.text_overlay import generate_overlay_text
from scripts.video.subtitle_generator import generate_subtitles
from scripts.audio.tts_generator import create_audio

def run_pipeline():

    print("🚀 AI-Commerce-OS iniciado\n")

    products = collect_products()

    for product in products:

        product_score = calculate_product_score(product)

        product["score_tecnico"] = product_score


    ranked_products = rank_products(products)

    products = [
        item["produto"]
        for item in ranked_products[:5]
    ]

    analyzed_products = []


    print(f"Produtos encontrados: {len(products)}")


    # FASE 1 - Inteligência

    for product in products:

        product_score = calculate_product_score(product)

        product["score_tecnico"] = product_score

        analysis = analyze_product(product)

        opportunity = analyze_opportunity(
            analysis,
            product["score_tecnico"]
        )

        analyzed_products.append(
            {
                "produto": product,
                "analise": analysis,
                "oportunidade": opportunity
            }
        )


    # Ranking

    top_products = rank_products(
        analyzed_products
    )[:3]


    print("\nTOP PRODUTOS:")
    
    for item in ranked_products[:5]:
        print(
            item["produto"]["nome"],
            "-",
            item["score"]
        )


    results = []


    # FASE 2 - Criativo

    for item in top_products:

        data = item["produto"]

        product = data["produto"]

        analysis = data["analise"]

        opportunity = data["oportunidade"]


        script = generate_ai_script(
            product,
            analysis,
            opportunity
        )


        content = generate_content(
            product,
            analysis,
            opportunity,
            script
        )

        caption = generate_caption(
            content
        )


        scenes = generate_scenes(
            product,
            content
        )

        subtitle_file = generate_subtitles(
            {
                "produto": product,
                "cenas": scenes     
                }
        )

        overlay_texts = generate_overlay_text(
            scenes
        )   

        asset_queries = generate_asset_queries(
            scenes
        )

        media_search = search_media(
            product,
            asset_queries
        )

        download_videos(
            product,
            media_search
        )


        media_folder = prepare_media_folder(
            product["nome"]
        )

        prepare_assets(product)

        action = decide_action(
            opportunity
        )

        audio_file = create_audio(
    {
        "text": content["texto_narracao"],
        "output_path": "output/audio/narracao.mp3"
    }
        )


        result = {
            "produto": product,
            "analise": analysis,
            "oportunidade": opportunity,
            "acao": action,
            "roteiro": script,
            "conteudo": content,
            "legenda": caption,
            "overlay_texts": overlay_texts,
            "cenas": scenes,
            "audio": str(audio_file),
            "asset_queries": asset_queries,
            "media_search": media_search,
            "media_folder": str(media_folder),
            "subtitle_file": str(subtitle_file)
        }

        video_project = build_video_project(result)

        render_video_project(result)

        save_product(result)

        export_product(result)

        results.append(result)

        generate_dashboard(results)


    return results



if __name__ == "__main__":

    pipeline_result = run_pipeline()

    print("\nProcesso finalizado.")