from pathlib import Path
import json


DASHBOARD = Path("output/dashboard.json")
HTML = Path("output/dashboard.html")


def create_viewer():

    with open(
        DASHBOARD,
        encoding="utf-8"
    ) as file:
        data = json.load(file)


    rows = ""

    for product in data["produtos"]:

        rows += f"""
        <tr>
            <td>{product["nome"]}</td>
            <td>{product["score"]}</td>
            <td>{product["acao"]}</td>
        </tr>
        """


    html = f"""
    <html>
    <head>
        <title>AI-Commerce-OS Dashboard</title>
    </head>

    <body>

    <h1>AI-Commerce-OS</h1>

    <p>
    Atualizado: {data["atualizado_em"]}
    </p>

    <table border="1">

    <tr>
        <th>Produto</th>
        <th>Score</th>
        <th>Ação</th>
    </tr>

    {rows}

    </table>

    </body>
    </html>
    """


    HTML.write_text(
        html,
        encoding="utf-8"
    )


if __name__ == "__main__":
    create_viewer()