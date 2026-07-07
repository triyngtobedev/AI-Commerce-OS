from database_manager import save_product, load_products


produto = {
    "produto": "Teste AI-Commerce",
    "score": 90,
    "potencial": "alto"
}


save_product(produto)

print(load_products())