from scripts.video.shopee_caption_generator import generate_shopee_caption

produto = {
    "nome": "Mini Aspirador Portátil",
    "categoria": "Casa"
}

conteudo = {
    "titulo": "Eu achei que esse mini aspirador era inútil... até testar",
    "descricao": "Resolvi testar esse gadget para descobrir se ele realmente ajuda nas pequenas sujeiras do dia a dia.",
    "texto_narracao": "Eu sempre tinha aquelas sujeiras pequenas no carro e na mesa que davam trabalho para tirar."
}

resultado = generate_shopee_caption(produto, conteudo)

print("\n===== RESULTADO =====")
print(resultado)
print("======================\n")

if resultado["titulo"] and resultado["hashtags"]:
    print("✅ Legenda Shopee gerada com sucesso.")
else:
    print("❌ Legenda veio vazia — algo falhou (ver mensagem de erro acima).")