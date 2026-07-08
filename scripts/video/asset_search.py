def generate_asset_queries(scenes):

    queries = []

    for scene in scenes["cenas"]:

        queries.append(
            {
                "tempo": scene["tempo"],
                "tipo": scene["tipo"],
                "busca": scene["visual"]
            }
        )

    return queries