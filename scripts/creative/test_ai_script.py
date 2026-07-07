from scripts.creative.ai_script_generator import generate_ai_script

produto = {
    "nome": "Mini Aspirador Portátil",
    "categoria": "Casa"
}


analise = {
    "score": 95,
    "publico_alvo": "Pessoas que gostam de praticidade"
}


resultado = generate_ai_script(
    produto,
    analise
)


print(resultado)