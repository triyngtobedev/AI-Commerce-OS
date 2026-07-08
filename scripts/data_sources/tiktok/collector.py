"""
TikTok Collector

Primeiro módulo do AI-Commerce-OS.

Responsável por coletar e organizar informações
de produtos encontrados no TikTok.
"""


def collect_products():
    """
    Simula a coleta de produtos encontrados no TikTok.

    Futuramente este módulo será conectado
    a fontes reais de dados.
    """

    products = [

        {
            "nome": "Mini Aspirador Portátil USB",
            "categoria": "Casa",
            "visualizacoes": 150000,
            "curtidas": 12000,
            "comentarios": 850
        },

        {
            "nome": "Luminária LED Inteligente RGB",
            "categoria": "Tecnologia",
            "visualizacoes": 90000,
            "curtidas": 7000,
            "comentarios": 400
        },

        {
            "nome": "Suporte Magnético Veicular para Celular",
            "categoria": "Automotivo",
            "visualizacoes": 120000,
            "curtidas": 9500,
            "comentarios": 620
        },

        {
            "nome": "Removedor de Pelos Pet Portátil",
            "categoria": "Pets",
            "visualizacoes": 180000,
            "curtidas": 16000,
            "comentarios": 1100
        },

        {
            "nome": "Organizador de Cabos Magnético",
            "categoria": "Tecnologia",
            "visualizacoes": 75000,
            "curtidas": 6000,
            "comentarios": 350
        },

        {
            "nome": "Garrafa Térmica Inteligente com Display",
            "categoria": "Utilidades",
            "visualizacoes": 210000,
            "curtidas": 22000,
            "comentarios": 1400
        },

        {
            "nome": "Escova Elétrica de Limpeza Multifuncional",
            "categoria": "Casa",
            "visualizacoes": 250000,
            "curtidas": 30000,
            "comentarios": 2200
        },

        {
            "nome": "Luz LED para Monitor com Controle",
            "categoria": "Setup",
            "visualizacoes": 130000,
            "curtidas": 10000,
            "comentarios": 700
        },

        {
            "nome": "Cortador de Legumes Manual 3 em 1",
            "categoria": "Cozinha",
            "visualizacoes": 170000,
            "curtidas": 14000,
            "comentarios": 900
        },

        {
            "nome": "Suporte Dobrável para Notebook",
            "categoria": "Escritório",
            "visualizacoes": 110000,
            "curtidas": 8500,
            "comentarios": 500
        }
    ]

    return products


if __name__ == "__main__":

    produtos = collect_products()

    for produto in produtos:
        print(produto)