import json
from pathlib import Path
from datetime import datetime


OUTPUT = Path("output/dashboard.json")


def generate_dashboard(results):
    """
    Cria painel geral dos produtos.
    """

    dashboard = {
        "atualizado_em": datetime.now().isoformat(),
        "produtos": []
    }


    for item in results:

        dashboard["produtos"].append(
            {
                "nome": item["produto"]["nome"],
                "score": item["oportunidade"]["score_venda"],
                "acao": item["acao"]
            }
        )


    OUTPUT.parent.mkdir(
        exist_ok=True
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            dashboard,
            file,
            ensure_ascii=False,
            indent=4
        )


    return dashboard