"""
TikTok Collector

Responsável por coletar e organizar
produtos encontrados nas fontes de dados.
"""

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]

SOURCE_FILE = ROOT_DIR / "database" / "products_source.json"



def collect_products():
    """
    Carrega produtos da fonte de dados.
    """

    if not SOURCE_FILE.exists():

        raise FileNotFoundError(
            "Arquivo products_source.json não encontrado."
        )


    with open(
        SOURCE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        products = json.load(file)


    return products



if __name__ == "__main__":

    products = collect_products()

    print(
        f"Produtos encontrados: {len(products)}"
    )

    for product in products:
        print(product)