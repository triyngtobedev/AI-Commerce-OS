"""
Research Pack — pacote de pesquisa antes da geração do roteiro.

Fornece fatos, fontes, cronologia e termos de busca para roteiros
editoriais com menor risco de conteúdo genérico ou afirmações sem fonte.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

# ask_ai importado lazy em generate_research_pack


RESEARCH_PACK_PROMPT = """Você é um pesquisador editorial de documentários YouTube dark.

Tema: {topic}
Categoria: {category}
Contexto adicional: {context}

Retorne APENAS JSON com esta estrutura:
{{
  "topic": "tema",
  "main_facts": ["fato verificável 1", "fato 2", ...],
  "sources": [
    {{"claim": "afirmação", "source": "nome da fonte", "url_hint": "domínio ou tipo", "confidence": "high|medium|low"}}
  ],
  "chronology": [
    {{"year": "2020", "event": "descrição do evento"}}
  ],
  "characters_and_companies": ["empresa/pessoa 1", ...],
  "real_image_search_terms_en": ["termo em inglês 1", ...],
  "real_image_search_terms_pt": ["termo em português 1", ...],
  "sensitive_claims": [
    {{"claim": "afirmação sensível", "risk": "high|medium|low", "needs_source": true}}
  ],
  "visual_opportunities": ["mapa da rota logística", "gráfico de crescimento", ...],
  "narrative_angles": ["ângulo 1", "ângulo 2"],
  "competitor_patterns": ["hook com número chocante", "timeline visual", ...]
}}

Regras:
- Fatos devem ser verificáveis; marque claims sensíveis
- Termos de busca em inglês para stock footage
- Não invente URLs — use url_hint descritivo
- Foque em visual storytelling editorial
"""


def _fallback_research_pack(topic: dict) -> dict:
    """Pack mínimo quando IA indisponível."""

    name = topic.get("nome", "tema")
    keywords = topic.get("keywords", []) or topic.get("tags", [])
    if isinstance(keywords, str):
        keywords = [keywords]

    en_terms = [f"{name} documentary", f"{name} factory", f"{name} logistics"]
    pt_terms = [name] + keywords[:5]

    return {
        "topic": name,
        "main_facts": [f"Documentário sobre {name}"],
        "sources": [],
        "chronology": [],
        "characters_and_companies": [name.split()[0] if name else "empresa"],
        "real_image_search_terms_en": en_terms,
        "real_image_search_terms_pt": pt_terms,
        "sensitive_claims": [],
        "visual_opportunities": ["establishing shot", "data visualization", "map"],
        "narrative_angles": ["como cresceu tão rápido", "impacto no mercado"],
        "competitor_patterns": ["hook com pergunta", "revelação no meio"],
        "generated_offline": True,
    }


def generate_research_pack(
    topic: dict,
    *,
    analysis: Optional[dict] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """Gera pacote de pesquisa para orientar roteiro e busca de mídia."""

    name = topic.get("nome", "")
    category = topic.get("categoria", topic.get("category", "documentário"))
    context = ""
    if analysis:
        context = json.dumps(
            {k: analysis.get(k) for k in ("resumo", "keywords", "angulo") if analysis.get(k)},
            ensure_ascii=False,
        )

    prompt = RESEARCH_PACK_PROMPT.format(
        topic=name,
        category=category,
        context=context or "nenhum",
    )

    try:
        from scripts.ai.router import ask_ai
        from scripts.utils.json_parser import safe_parse_json

        response = ask_ai(prompt, context_type="analysis")
        pack = safe_parse_json(response)
        if not isinstance(pack, dict) or not pack.get("topic"):
            pack = _fallback_research_pack(topic)
    except Exception:
        pack = _fallback_research_pack(topic)

    pack.setdefault("topic", name)
    pack["search_terms_en"] = pack.get("real_image_search_terms_en", [])
    pack["search_terms_pt"] = pack.get("real_image_search_terms_pt", [])

    if output_dir:
        path = Path(output_dir) / "research_pack.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")

    return pack


def validate_claims_against_pack(script: dict, pack: dict) -> dict:
    """Identifica claims sensíveis sem fonte no roteiro."""

    sensitive = pack.get("sensitive_claims", [])
    sourced_claims = {s.get("claim", "").lower() for s in pack.get("sources", []) if s.get("claim")}
    flagged = []

    narration = " ".join(str(v) for v in script.values() if isinstance(v, str)).lower()

    for item in sensitive:
        claim = item.get("claim", "")
        if not claim:
            continue
        if item.get("needs_source") and claim.lower() not in sourced_claims:
            if any(word in narration for word in claim.lower().split()[:3]):
                flagged.append({
                    "claim": claim,
                    "risk": item.get("risk", "medium"),
                    "action": "add_source_or_remove",
                })

    return {
        "flagged_claims": flagged,
        "safe_to_proceed": len(flagged) == 0 or all(f["risk"] == "low" for f in flagged),
    }
