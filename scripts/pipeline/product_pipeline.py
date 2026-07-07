from scripts.data_sources.tiktok.collector import collect_products
from scripts.ai.analysts.ai_analyst import analyze_product
from scripts.affiliate.opportunity_engine import analyze_opportunity
from database.database_manager import save_product


def run_pipeline():
    """
    Executa o fluxo completo de análise de produtos.
    """

    products = collect_products()

    results = []

    for product in products:
        analysis = analyze_product(product)

        opportunity = analyze_opportunity(analysis)

        result = {
            "produto": product,
            "analise": analysis,
            "oportunidade": opportunity
        }

        save_product(result)

        results.append(result)

    return results


if __name__ == "__main__":
    pipeline_result = run_pipeline()

    for item in pipeline_result:
        print("=" * 40)
        print(item["produto"]["nome"])
        print(item["oportunidade"])