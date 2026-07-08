def generate_overlay_text(scenes):

    texts = []

    for scene in scenes["cenas"]:

        texts.append(
            {
                "tempo": scene["tempo"],
                "texto": scene["narracao"]
            }
        )

    return texts