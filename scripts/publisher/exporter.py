import json
from pathlib import Path


OUTPUT_DIR = Path("output")


def slugify(text):
    return (
        text.lower()
        .replace(" ", "-")
        .replace("/", "-")
    )


def export_product(result):

    produto = result["produto"]["nome"]

    folder = OUTPUT_DIR / slugify(produto)

    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    files = {
        "analysis.json": result["analise"],
        "scenes.json": result["cenas"],
        "opportunity.json": result["oportunidade"],
        "decision.json": {
            "acao": result["acao"]
        },
        "script.json": result["roteiro"],
        "content.json": result["conteudo"],
        "caption.json": result["legenda"],
        "asset_queries.json": result["asset_queries"],

    
    }


    for filename, data in files.items():

        with open(
            folder / filename,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )


    (folder / "roteiro.txt").write_text(
        json.dumps(
            result["roteiro"],
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    (folder / "descricao.txt").write_text(
        result["conteudo"]["descricao"],
        encoding="utf-8"
    )


    (folder / "narracao.txt").write_text(
        result["conteudo"]["texto_narracao"],
        encoding="utf-8"
    )


    (folder / "hashtags.txt").write_text(
        "\n".join(
            result["conteudo"]["hashtags"]
        ),
        encoding="utf-8"
    )