from scripts.content.content_generator import generate_content
from scripts.creative.ai_script_generator import generate_ai_script
from scripts.data_sources.tiktok.collector import collect_products
from scripts.ai.analysts.ai_analyst import analyze_product
from scripts.affiliate.opportunity_engine import analyze_opportunity
from scripts.affiliate.product_ranker import rank_products
from database.database_manager import save_product
from scripts.publisher.exporter import export_product
from scripts.video.scene_generator import generate_scenes
from scripts.video.media_manager import prepare_media_folder


def run_pipeline():

    print("🚀 AI-Commerce-OS iniciado\n")

    products = collect_products()

    analyzed_products = []


    print(f"Produtos encontrados: {len(products)}")


    # FASE 1 - Inteligência

    for product in products:

        analysis = analyze_product(product)

        opportunity = analyze_opportunity(
            analysis
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
    
    for item in top_products:
        print(
            item["produto"]["nome"],
            "-",
            item["oportunidade"]["score_venda"]
        )


    results = []


    # FASE 2 - Criativo

    for item in top_products:

        product = item["produto"]

        analysis = item["analise"]

        opportunity = item["oportunidade"]


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


        scenes = generate_scenes(
            product,
            content
        )


        media_folder = prepare_media_folder(
            product["nome"]
        )


        result = {
            "produto": product,
            "analise": analysis,
            "oportunidade": opportunity,
            "roteiro": script,
            "conteudo": content,
            "cenas": scenes,
            "media_folder": str(media_folder)
        }


        save_product(result)

        export_product(result)

        results.append(result)


    return results



if __name__ == "__main__":

    pipeline_result = run_pipeline()

    print("\nProcesso finalizado.")