import json
from pathlib import Path


def build_video_project(result):

    product = result["produto"]["nome"]

    folder = Path("output") / product.lower().replace(" ", "-")


    project = {
        "produto": product,
        "duracao": result["conteudo"]["duracao"],
        "cenas": result["cenas"],
        "narracao": result["conteudo"]["texto_narracao"],
        "legenda": result["legenda"],
        "status": "READY_FOR_RENDER"
    }


    with open(
        folder / "video_project.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            project,
            file,
            ensure_ascii=False,
            indent=4
        )


    return project