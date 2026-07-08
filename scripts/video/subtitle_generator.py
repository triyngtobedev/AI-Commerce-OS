from pathlib import Path


def generate_subtitles(result):

    product = result["produto"]["nome"]

    folder = (
        Path("output")
        / product.lower().replace(" ", "-")
    )

    subtitle_file = folder / "captions.srt"


    scenes = result.get(
        "cenas",
        {}
    ).get(
        "cenas",
        []
    )


    with open(
        subtitle_file,
        "w",
        encoding="utf-8"
    ) as file:

        index = 1

        for scene in scenes:

            tempo = scene["tempo"]

            inicio, fim = tempo.split("-")

            texto = scene["narracao"]


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


    return subtitle_file