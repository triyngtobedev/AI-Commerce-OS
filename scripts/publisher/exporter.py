import json
from pathlib import Path


OUTPUT_DIR = Path("output")


def slugify(text):
    """
    Converte nome do produto para nome de pasta.
    """

    return (
        text.lower()
        .replace(" ", "-")
        .replace("/", "-")
    )


def export_product(result):
    """
    Exporta todos os arquivos do produto.
    """

    produto = result["produto"]["nome"]

    folder = OUTPUT_DIR / slugify(produto)

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # JSONs

    with open(folder / "analysis.json", "w", encoding="utf-8") as file:
        json.dump(
            result["analise"],
            file,
            ensure_ascii=False,
            indent=4
        )

    with open(folder / "scenes.json", "w", encoding="utf-8") as file:
        json.dump(
            result["cenas"],
            file,
            ensure_ascii=False,
            indent=4
        )

    with open(folder / "opportunity.json", "w", encoding="utf-8") as file:
        json.dump(
            result["oportunidade"],
            file,
            ensure_ascii=False,
            indent=4
        )

    with open(folder / "script.json", "w", encoding="utf-8") as file:
        json.dump(
            result["roteiro"],
            file,
            ensure_ascii=False,
            indent=4
        )

    with open(folder / "content.json", "w", encoding="utf-8") as file:
        json.dump(
            result["conteudo"],
            file,
            ensure_ascii=False,
            indent=4
        )

    # TXT

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