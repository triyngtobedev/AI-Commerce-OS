"""
AI-Commerce-OS

Sistema principal de análise de produtos.
"""

from scripts.data_sources.tiktok.collector import collect_products
from scripts.ai.analysts.analyst import analyze_product


def run():

    print("🚀 AI-Commerce-OS iniciado\n")

    products = collect_products()

    print(f"Produtos encontrados: {len(products)}\n")

    for product in products:

        analysis = analyze_product(product)

        print("--------------------------------")
        print(f"Produto: {analysis['produto']}")
        print(f"Score: {analysis['score']}")
        print(f"Potencial: {analysis['potencial']}")
        print(f"Engagement: {analysis['engagement_rate']}%")


if __name__ == "__main__":
    run()