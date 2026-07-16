from scripts.content.content_generator import generate_content

produto = {
    "nome": "Mini Aspirador Portátil",
    "categoria": "Casa"
}

analise = {
    "score": 95,
    "potencial": "alto"
}

oportunidade = {
    "score_venda": 90,
    "decisao": "CRIAR_VIDEO"
}

roteiro = {
    "hook": "Eu não sabia que precisava disso...",
    "problema": "Sujeira em lugares difíceis.",
    "demonstracao": "Mostra o aspirador funcionando.",
    "beneficio": "Mais praticidade.",
    "cta": "Clique no link."
}

resultado = generate_content(
    produto,
    analise,
    oportunidade,
    roteiro
)

print(resultado)