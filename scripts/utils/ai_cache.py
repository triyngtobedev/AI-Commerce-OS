import json
from pathlib import Path


CACHE_DIR = Path("database/ai_cache")


def get_cache_path(category, product_name):

    filename = (
        product_name
        .lower()
        .replace(" ", "-")
        + ".json"
    )

    return CACHE_DIR / category / filename



def save_cache(category, product_name, data):

    path = get_cache_path(
        category,
        product_name
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )



def load_cache(category, product_name):

    path = get_cache_path(
        category,
        product_name
    )

    if not path.exists():
        return None


    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)