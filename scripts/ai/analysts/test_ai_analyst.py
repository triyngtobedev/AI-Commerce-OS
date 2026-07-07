from scripts.ai.analysts.ai_analyst import analyze_product

produto = {
    "nome": "Mini Aspirador Portátil",
    "categoria": "Casa",
    "visualizacoes": 150000,
    "curtidas": 12000,
    "comentarios": 850
}


resultado = analyze_product(produto)


print(resultado)