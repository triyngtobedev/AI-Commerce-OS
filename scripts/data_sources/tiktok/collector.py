"""
TikTok Collector

Primeiro módulo do AI-Commerce-OS.

Responsável por coletar e organizar informações
de produtos encontrados no TikTok.
"""


def collect_products():
    """
    Simula a coleta de produtos.

    Futuramente este módulo será conectado
    a fontes reais de dados.
    """

    products = [
        {
            "nome": "Mini Aspirador Portátil",
            "categoria": "Casa",
            "visualizacoes": 150000,
            "curtidas": 12000,
            "comentarios": 850
        },
        {
            "nome": "Luminária LED Inteligente",
            "categoria": "Tecnologia",
            "visualizacoes": 90000,
            "curtidas": 7000,
            "comentarios": 400
        }
    ]

    return products


if __name__ == "__main__":
    produtos = collect_products()

    for produto in produtos:
        print(produto)