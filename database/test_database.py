from database.database_manager import save_product, load_products


produto = {
    "produto": {
        "nome": "Teste AI-Commerce"
    },
    "analise": {
        "score": 90,
        "potencial": "alto"
    }
}


save_product(produto)

print(load_products())
