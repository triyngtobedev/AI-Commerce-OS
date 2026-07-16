from scripts.creative.script_generator import generate_script


produto = {
    "nome": "Mini Aspirador Portátil"
}


oportunidade = {
    "ganchos": [
        "Eu não sabia que precisava disso até testar..."
    ]
}


resultado = generate_script(
    produto,
    oportunidade
)


print(resultado)
