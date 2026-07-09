from pathlib import Path



def generate_subtitles(result):

    product = result["produto"]["nome"]


    folder = (
        Path("output")
        / product.lower().replace(" ", "-")
    )


    folder.mkdir(
        parents=True,
        exist_ok=True
    )


    subtitle_file = (
        folder
        / "captions.srt"
    )


    cenas_data = result.get(
        "cenas",
        []
    )


    # compatibilidade caso venha como {"cenas":[]}

    if isinstance(cenas_data, dict):

        scenes = cenas_data.get(
            "cenas",
            []
        )

    else:

        scenes = cenas_data



    # fallback usando roteiro caso cenas estejam vazias

    if not scenes:

        texto = (
            result
            .get("conteudo", {})
            .get(
                "texto_narracao",
                ""
            )
        )


        if texto:

            scenes = [
                {
                    "tempo": "0-30",
                    "narracao": texto
                }
            ]



    with open(
        subtitle_file,
        "w",
        encoding="utf-8"
    ) as file:


        index = 1


        for scene in scenes:


            tempo = scene.get(
                "tempo",
                "0-5"
            )


            inicio, fim = tempo.split("-")



            texto = scene.get(
                "narracao",
                scene.get(
                    "texto",
                    ""
                )
            )



            if not texto:

                continue



            file.write(
                f"{index}\n"
            )


            file.write(
                f"00:00:{inicio},000 --> 00:00:{fim},000\n"
            )


            file.write(
                f"{texto}\n\n"
            )


            index += 1



    print(
        f"📝 Legenda criada: {subtitle_file.resolve()}"
    )


    return subtitle_file.resolve()