import json
from pathlib import Path


OUTPUT_DIR = Path("output")



def slugify(text):

    return (
        text
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
    )



def export_product(result):

    produto = (
        result
        .get("produto", {})
        .get(
            "nome",
            "produto"
        )
    )


    folder = (
        OUTPUT_DIR
        /
        slugify(produto)
    )


    folder.mkdir(
        parents=True,
        exist_ok=True
    )



    conteudo = result.get(
        "conteudo",
        {}
    )


    if not isinstance(
        conteudo,
        dict
    ):

        conteudo = {}



    files = {

        "analysis.json":
            result.get(
                "analise",
                {}
            ),


        "scenes.json":
            result.get(
                "cenas",
                {}
            ),


        "opportunity.json":
            result.get(
                "oportunidade",
                {}
            ),


        "decision.json":
            {
                "acao":
                    result.get(
                        "acao",
                        "avaliar"
                    )
            },


        "script.json":
            result.get(
                "roteiro",
                {}
            ),


        "content.json":
            conteudo,


        "caption.json":
            result.get(
                "legenda",
                {}
            ),


        "asset_queries.json":
            result.get(
                "asset_queries",
                []
            )

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



    # =========================
    # ARQUIVOS TEXTO
    # =========================


    (folder / "roteiro.txt").write_text(

        json.dumps(
            result.get(
                "roteiro",
                {}
            ),
            ensure_ascii=False,
            indent=2
        ),

        encoding="utf-8"

    )



    (folder / "descricao.txt").write_text(

        conteudo.get(
            "descricao",
            ""
        ),

        encoding="utf-8"

    )



    (folder / "narracao.txt").write_text(

        conteudo.get(
            "texto_narracao",
            ""
        ),

        encoding="utf-8"

    )



    hashtags = conteudo.get(
        "hashtags",
        []
    )


    if not isinstance(
        hashtags,
        list
    ):

        hashtags = [
            str(hashtags)
        ]



    (folder / "hashtags.txt").write_text(

        "\n".join(
            hashtags
        ),

        encoding="utf-8"

    )



    print(
        f"📦 Produto exportado: {folder}"
    )


    return folder