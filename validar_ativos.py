import os

from scripts.utils.slug import slugify


def verificar_produtos():
    base_path = "output"

    try:
        from scripts.data_sources.tiktok.collector import collect_products
        produtos = [
            slugify(p["nome"])
            for p in collect_products()
        ]
    except Exception:
        produtos = [
            "mini-aspirador-portatil",
            "luminaria-led-inteligente",
        ]
    
    print("--- Relatório de Ativos ---")
    for produto in produtos:
        caminho_produto = os.path.join(base_path, produto)
        caminho_media = os.path.join("media", produto)
        
        # Verifica se o vídeo final já existe
        if os.path.exists(os.path.join(caminho_produto, "video_final.mp4")):
            status = "✅ PRONTO"
        else:
            status = "❌ FALTANDO VÍDEO"
            
        # Verifica se existem mídias base para o produto
        tem_midia = os.path.exists(caminho_media) and len(os.listdir(caminho_media)) > 0
        status_midia = "✅ Mídias OK" if tem_midia else "⚠️ SEM MÍDIAS (Adicionar agora!)"
        
        print(f"Produto: {produto}")
        print(f"  Status: {status}")
        print(f"  Mídias: {status_midia}")
        print("-" * 30)

if __name__ == "__main__":
    verificar_produtos()