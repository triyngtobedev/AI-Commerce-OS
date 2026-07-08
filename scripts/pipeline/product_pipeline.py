from scripts.content.content_generator import generate_content
from scripts.creative.ai_script_generator import generate_ai_script
from scripts.data_sources.tiktok.collector import collect_products
from scripts.ai.analysts.ai_analyst import analyze_product
from scripts.affiliate.opportunity_engine import analyze_opportunity
from database.database_manager import save_product
from scripts.publisher.exporter import export_product
from scripts.video.scene_generator import generate_scenes
from scripts.video.media_manager import prepare_media_folder


def run_pipeline():
    """
    Executa o fluxo completo de análise de produtos.
    """

    products = collect_products()

    results = []

    for product in products:
        analysis = analyze_product(product)

        opportunity = analyze_opportunity(analysis)

        script = generate_ai_script(product, analysis, opportunity
        )

        content = generate_content(
            product,
            analysis,
            opportunity,
            script,
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

    for item in pipeline_result:
        print("=" * 40)
        print(item["produto"]["nome"])

        print("\nANÁLISE:")
        print(item["analise"])

        print("\nOPORTUNIDADE:")
        print(item["oportunidade"])

        print("\nROTEIRO:")
        print(item["roteiro"])

        print("\nCONTEÚDO:")
        print(item["conteudo"])