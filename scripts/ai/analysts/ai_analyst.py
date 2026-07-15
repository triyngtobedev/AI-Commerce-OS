import json
import re
from scripts.utils.prompt_loader import load_prompt
from scripts.ai.router import ask_ai
from scripts.utils.json_parser import parse_json
from scripts.utils.ai_cache import load_cache, save_cache

def analyze_product(product):
    """
    Analisa um produto usando IA com sistema de cache e tratamento de erros.
    """
    # Garante limpeza no nome para evitar erros de arquivo
    product_name = product.get("nome", "produto_sem_nome").strip()

    # 1. Tenta carregar do cache
    cached = load_cache("analysis", product_name)
    if cached:
        print(f"♻️ Cache encontrado: {product_name}")
        return cached

    print(f"🔍 Nenhum cache para {product_name}. Preparando chamada de IA...")

    base_prompt = load_prompt("product_analysis")
    product_data = json.dumps(product, ensure_ascii=False, indent=2)
    final_prompt = f"{base_prompt}\n\nAnalise este produto:\n{product_data}"

    # 2. Execução protegida
    try:
        print("⏳ Chamando roteador de IA...")
        response = ask_ai(final_prompt, "analysis")
        
        # Limpeza robusta do JSON antes do parse
        if isinstance(response, str):
            # Remove blocos Markdown e extrai apenas o conteúdo entre { }
            cleaned_response = re.sub(r'```json\s*|\s*```', '', response)
            start = cleaned_response.find('{')
            end = cleaned_response.rfind('}') + 1
            if start != -1 and end != -1:
                cleaned_response = cleaned_response[start:end]
            
            analysis = json.loads(cleaned_response)
        else:
            analysis = response
        
        print("✅ Análise recebida com sucesso.")
        
        # 3. Salva no cache
        print("💾 Salvando no cache...")
        save_cache("analysis", product_name, analysis)
        
        return analysis

    except Exception as e:
        print(f"❌ ERRO CRÍTICO ao processar {product_name}: {e}")
        # Retorno de segurança para o pipeline não travar
        return {
            "analise": "fallback", 
            "pontos_fortes": ["Não disponível"], 
            "pontos_fracos": ["Não disponível"]
        }