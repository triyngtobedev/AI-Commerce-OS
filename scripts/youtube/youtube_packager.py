"""
YouTube Packager — embalagem editorial completa para publicação.

Gera youtube_package.json, thumbnail brief e variações de título.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def _extract_hook_phrase(content: dict, script: dict) -> str:
    hook = script.get("hook", "") if script else ""
    if hook:
        first_sentence = hook.replace("[PAUSA]", "").split(".")[0].strip()
        if first_sentence:
            return first_sentence[:80]
    return content.get("titulo", "")[:80]


def generate_thumbnail_brief(
    topic: str,
    content: dict,
    *,
    script: Optional[dict] = None,
    scenes: Optional[dict] = None,
    strategy: Optional[dict] = None,
) -> dict:
    """Brief editorial para thumbnail no estilo dark documental."""

    hook_phrase = _extract_hook_phrase(content, script or {})
    thumbnail_scene = None

    if scenes:
        for scene in scenes.get("cenas", []):
            if scene.get("thumbnail_potential") or scene.get("tipo") == "hook":
                thumbnail_scene = scene
                break

    visual = ""
    if thumbnail_scene:
        visual = thumbnail_scene.get("must_show") or thumbnail_scene.get("visual", "")

    ideas = [
        {
            "concept": "Tensão central",
            "subject": visual or topic,
            "text_overlay": hook_phrase[:40] if len(hook_phrase) > 20 else "",
            "mood": "dark dramatic high contrast",
            "composition": "subject center, dark vignette, minimal text",
        },
        {
            "concept": "Curiosidade",
            "subject": topic.split()[0] if topic else "subject",
            "text_overlay": "Como?",
            "mood": "mysterious intrigue",
            "composition": "close-up object/symbol, bold contrast",
        },
        {
            "concept": "Escala/impacto",
            "subject": visual or "factory warehouse logistics",
            "text_overlay": "",
            "mood": "epic scale documentary",
            "composition": "wide shot, dramatic lighting, no template look",
        },
    ]

    return {
        "topic": topic,
        "style_reference": "MagnatesMedia, Fern, Hoog — dark documentary",
        "rules": [
            "Pouco texto (máx 3-4 palavras)",
            "Contraste forte",
            "Rosto/objeto/símbolo central",
            "Tensão visual e curiosidade",
            "Sem cara de template genérico",
        ],
        "ideas": ideas,
        "recommended": ideas[0],
        "color_palette": "dark background, accent red/orange or cold blue",
        "dimensions": "1280x720",
    }


def generate_youtube_package(
    result: dict,
    *,
    export_folder: Optional[Path] = None,
) -> dict:
    """Gera pacote YouTube editorial completo."""

    content = result.get("conteudo", {}) or {}
    script = result.get("roteiro", {}) or {}
    strategy = result.get("estrategia", {}) or {}
    scenes = result.get("cenas", {}) or {}
    topic = result.get("produto", {}).get("nome", content.get("titulo", "video"))
    youtube_meta = result.get("youtube_metadata", {}) or {}

    titulo = content.get("titulo", topic)
    alt_titles = content.get("titulo_alternativos", [])

    # Gera variações se insuficientes
    if len(alt_titles) < 5:
        base = titulo.rstrip(".")
        generated = [
            f"{base}?",
            f"A verdade sobre {topic}",
            f"Como {topic} mudou tudo",
            f"{topic}: o que ninguém te conta",
            f"Por dentro de {topic}",
        ]
        for t in generated:
            if t not in alt_titles and t != titulo:
                alt_titles.append(t)
            if len(alt_titles) >= 5:
                break

    chapters = youtube_meta.get("capitulos") or result.get("chapters", [])
    tags = content.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]

    descricao = content.get("descricao", "")
    pinned_comment = content.get(
        "comentario_fixado",
        f"Qual parte te surpreendeu mais sobre {topic}? Comenta 👇",
    )

    thumbnail_brief = generate_thumbnail_brief(
        topic, content, script=script, scenes=scenes, strategy=strategy,
    )

    package = {
        "platform": "youtube",
        "topic": topic,
        "titulo": titulo,
        "titulo_variacoes": alt_titles[:5],
        "descricao": descricao,
        "tags": tags,
        "capitulos": chapters,
        "categoria": content.get("categoria_youtube", "Education"),
        "idioma": content.get("idioma", "pt-BR"),
        "pinned_comment": pinned_comment,
        "thumbnail_brief": thumbnail_brief,
        "thumbnail_ideas": thumbnail_brief["ideas"],
        "seo": {
            "primary_keyword": topic,
            "secondary_keywords": tags[:8],
            "hook_for_description": _extract_hook_phrase(content, script),
        },
        "status": "READY_TO_UPLOAD",
    }

    if export_folder:
        folder = Path(export_folder)
        folder.mkdir(parents=True, exist_ok=True)

        (folder / "youtube_package.json").write_text(
            json.dumps(package, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (folder / "thumbnail_brief.json").write_text(
            json.dumps(thumbnail_brief, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return package
