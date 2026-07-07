import json
import os


DATABASE_FILE = "database/products.json"


def load_products():
    """
    Carrega produtos existentes.
    """

    if not os.path.exists(DATABASE_FILE):
        return []

    with open(
        DATABASE_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_product(product):
    """
    Salva um novo produto no banco.
    """

    products = load_products()

    products.append(product)

    with open(
        DATABASE_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            indent=4
        )

    return product