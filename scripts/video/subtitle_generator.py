from pathlib import Path


def generate_subtitles(data):

    product = data["produto"]["nome"]

    folder = (
        Path("output")
        / product.lower().replace(" ", "-")
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    subtitle_file = folder / "captions.srt"

    cenas = data["cenas"]["cenas"]

    with open(
        subtitle_file,
        "w",
        encoding="utf-8"
    ) as file:

        index = 1

        for cena in cenas:

            file.write(
                f"{index}\n"
            )

            file.write(
                f"{cena['tempo'].replace('-', ' --> ')}\n"
            )

            file.write(
                f"{cena['narracao']}\n\n"
            )

            index += 1


    return subtitle_file