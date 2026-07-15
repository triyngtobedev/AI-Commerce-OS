def generate_scenes(product, content, creative_strategy=None): # <-- NOVO: Recebendo a estratégia
    """
    Transforma conteúdo em cenas visuais específicas
    para busca de mídia e geração de legenda, utilizando
    a estratégia criativa quando disponível.
    """

    nome = product["nome"]

    narracao = content.get("texto_narracao", "")
    descricao = content.get("descricao", narracao)

    # --- NOVO: Extraindo dados da Estratégia Criativa ---
    estilo_visual = ""
    gancho_visual = ""
    cta_texto_estrategia = ""

    if creative_strategy:
        estilo_visual = creative_strategy.get("estilo_visual", "")
        
        # Tratando diferentes formatos que a IA pode retornar no JSON de estratégia
        gancho = creative_strategy.get("gancho", {})
        if isinstance(gancho, dict):
            gancho_visual = gancho.get("visual", "")
        elif isinstance(gancho, str):
            gancho_visual = gancho
            
        cta = creative_strategy.get("call_to_action", "")
        if isinstance(cta, dict):
            cta_texto_estrategia = cta.get("texto", "")
        elif isinstance(cta, str):
            cta_texto_estrategia = cta

    # Fallbacks se a estratégia estiver vazia
    sufixo_estilo = f", {estilo_visual}" if estilo_visual else ""
    visual_hook_final = gancho_visual if gancho_visual else f"person discovering a problem solved by {nome}, before and after situation"
    narracao_cta_final = cta_texto_estrategia if cta_texto_estrategia else "Clique e garanta o seu."

    scenes = {
        "produto": nome,
        "cenas": [
            {
                "tempo": "0-3",
                "tipo": "hook",
                "visual": f"{visual_hook_final}{sufixo_estilo}",
                "narracao": narracao
            },
            {
                "tempo": "3-15",
                "tipo": "demonstracao",
                "visual": f"person using {nome} in real life, close up demonstration, product in action{sufixo_estilo}",
                "narracao": descricao
            },
            {
                "tempo": "15-25",
                "tipo": "beneficio",
                "visual": f"clean result after using {nome}, happy person showing improvement{sufixo_estilo}",
                "narracao": "Uma solução simples para facilitar o seu dia a dia."
            },
            {
                "tempo": "25-30",
                "tipo": "cta",
                "visual": f"{nome} product showcase, modern commercial style, close up{sufixo_estilo}",
                "narracao": narracao_cta_final
            }
        ]
    }

    return scenes