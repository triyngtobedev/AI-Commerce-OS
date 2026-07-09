import json
from pathlib import Path



def slugify(text):

    return (
        text
        .lower()
        .replace(" ", "-")
        .replace("/", "-")
    )



def build_video_project(result):

    product = (
        result
        .get("produto", {})
        .get(
            "nome",
            "produto"
        )
    )


    folder = (
        Path("output")
        /
        slugify(product)
    )


    folder.mkdir(
        parents=True,
        exist_ok=True
    )



    conteudo = result.get(
        "conteudo",
        {}
    )


    project = {

        "produto": product,


        "duracao":
            conteudo.get(
                "duracao",
                30
            ),


        "cenas":
            result.get(
                "cenas",
                []
            ),


        "narracao":
            conteudo.get(
                "texto_narracao",
                ""
            ),


        "legenda":
            result.get(
                "legenda",
                {}
            ),


        "audio":
            result.get(
                "audio"
            ),


        "subtitle_file":
            result.get(
                "subtitle_file"
            ),


        "status":
            "READY_FOR_RENDER"

    }



    file = (
        folder
        /
        "video_project.json"
    )



    with open(
        file,
        "w",
        encoding="utf-8"
    ) as f:


        json.dump(
            project,
            f,
            ensure_ascii=False,
            indent=4
        )



    return project