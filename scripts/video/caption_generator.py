def generate_caption(content):

    hashtags = content.get(
        "hashtags",
        content.get("tags", []),
    )

    if not isinstance(hashtags, list):
        hashtags = [str(hashtags)]

    return {
        "legenda": content.get("descricao", ""),
        "hashtags": hashtags,
    }