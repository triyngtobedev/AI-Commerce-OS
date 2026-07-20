"""
Media Search Orchestrator — busca multi-query com ranking editorial.

Prioridade: footage real → foto animada → motion graphics → IA → T2V.
"""

from __future__ import annotations

from typing import Any, Optional

from scripts.core.visual_intent_engine import resolve_visual_intent
from scripts.video.asset_ranking import pick_ranked_assets, score_asset
from scripts.video.media_providers.relevance import MIN_PHOTO_RELEVANCE_SCORE, MIN_RELEVANCE_SCORE
from scripts.video.pexels_provider import search_pexels
from scripts.video.pixabay_provider import search_pixabay
from scripts.video.query_localizer import localize_search_query, should_prioritize_wikimedia
from scripts.video.wikimedia_provider import search_wikimedia

QUERY_TYPES = (
    "factual",
    "visual",
    "emotional",
    "historical",
    "symbolic",
    "alt_en",
    "alt_pt",
)

# Mapeamento tipo editorial → queries emocionais/simbólicas
_EMOTION_QUERY_SUFFIX = {
    "impact": "dramatic historical impact ancient documentary",
    "mystery": "mysterious dark ancient atmosphere cinematic",
    "calm": "contemplative atmospheric",
    "warning": "crisis tension documentary",
    "tension": "conflict pressure documentary",
    "suspense": "suspense tension hidden secret documentary",
    "curiosity": "investigation discovery",
    "revelation": "dramatic revelation historical truth exposed",
    "wonder": "awe inspiring scale",
}

_SCENE_TYPE_KEYWORDS = {
    "hook": "mysterious revelation ancient secret documentary",
    "context": "establishing context overview",
    "contexto": "establishing context overview",
    "contexto_historico": "ancient civilization historical ruins archive",
    "character": "portrait person company",
    "conflict": "conflict tension struggle",
    "data": "statistics chart infographic",
    "timeline": "historical timeline events",
    "map": "geographic map location",
    "quote": "document text headline",
    "evidence": "document proof newspaper",
    "turning_point": "pivotal moment change",
    "revelacao": "hidden truth exposed historical evidence",
    "misterio": "ancient mystery unsolved conspiracy archive",
    "climax": "peak tension dramatic",
    "resolution": "conclusion aftermath legacy",
    "consequencias": "impact consequences aftermath",
    "impacto": "modern impact legacy",
    "encerramento": "dramatic conclusion historical documentary cinematic",
    "desenvolvimento_1": "process detail investigation",
    "desenvolvimento_2": "expansion scale growth",
}


def generate_scene_queries(
    scene: dict,
    *,
    topic: str = "",
    asset_queries: Optional[list[str]] = None,
) -> dict[str, str]:
    """Gera múltiplas queries por cena para busca editorial."""

    visual = scene.get("visual", "") or scene.get("must_show", "")
    tipo = scene.get("scene_type") or scene.get("tipo", "")
    emotion = scene.get("emotion", "calm")
    must_show = scene.get("must_show", visual)
    topic_words = topic or scene.get("topic", "")

    base_en = localize_search_query(must_show or visual or topic_words)
    base_pt = scene.get("busca_pt") or must_show or visual

    scene_kw = _SCENE_TYPE_KEYWORDS.get(tipo, "documentary footage")
    emotion_suffix = _EMOTION_QUERY_SUFFIX.get(emotion, "documentary cinematic")

    queries: dict[str, str] = {
        "factual": base_en,
        "visual": f"{base_en} {scene_kw}".strip(),
        "emotional": f"{base_en} {emotion_suffix}".strip(),
        "historical": f"{base_en} historical archive documentary".strip(),
        "symbolic": f"{base_en} metaphor symbolic representation".strip(),
        "alt_en": localize_search_query(f"{topic_words} {scene_kw}".strip()),
        "alt_pt": base_pt if base_pt else base_en,
    }

    if asset_queries:
        for i, q in enumerate(asset_queries[:3]):
            queries[f"asset_{i}"] = localize_search_query(q)

    return queries


def _search_provider(
    provider: str,
    query: str,
    *,
    photos_only: bool = False,
) -> tuple[list[dict], list[dict]]:
    if provider == "wikimedia":
        result = search_wikimedia(query, limit=12)
        return [], result.get("photos", [])
    if provider == "pixabay":
        result = search_pixabay(query, orientation="landscape")
        if photos_only:
            return [], result.get("photos", [])
        return result.get("videos", []), result.get("photos", [])
    if provider == "pexels":
        result = search_pexels(query, orientation="landscape")
        if photos_only:
            return [], result.get("photos", [])
        return result.get("videos", []), result.get("photos", [])
    return [], []


def _provider_order(query_item: dict) -> list[str]:
    tipo = query_item.get("tipo", "")
    if should_prioritize_wikimedia(tipo):
        return ["wikimedia", "pixabay", "pexels"]
    return ["pexels", "pixabay", "wikimedia"]


def search_and_rank_scene(
    query_item: dict,
    *,
    scene: Optional[dict] = None,
    topic: str = "",
    used_ids: Optional[set] = None,
    recent_selections: Optional[list] = None,
    prefer_image: bool = False,
    min_candidates: int = 3,
) -> list[dict]:
    """
    Busca em múltiplas fontes e retorna candidatos ranqueados.

    Cada candidato inclui score composto e metadados de licença.
    """

    scene = scene or {}
    scene_queries = query_item.get("scene_queries") or generate_scene_queries(
        {**scene, **query_item},
        topic=topic,
        asset_queries=query_item.get("asset_queries"),
    )

    visual_intent = query_item.get("visual_intent")
    emotion = query_item.get("emotion", "calm")
    tipo = query_item.get("tipo", "")
    narrative_moment = tipo
    style = query_item.get("style", "")
    camera = query_item.get("camera", "")
    avoid = query_item.get("avoid")

    spec = resolve_visual_intent({
        "visual_intent": visual_intent,
        "emotion": emotion,
        "camera_motion": camera or query_item.get("camera_motion", "slow_push"),
    })

    used = used_ids or set()
    all_candidates: list[dict] = []
    seen_urls: set[str] = set()

    for query_type, query in scene_queries.items():
        if not query:
            continue

        for provider in _provider_order(query_item):
            videos, photos = _search_provider(
                provider,
                query,
                photos_only=prefer_image,
            )

            for media_type, items in (("video", videos), ("photo", photos)):
                if prefer_image and media_type == "video":
                    continue

                ranked = pick_ranked_assets(
                    query,
                    items,
                    media_type=media_type,
                    visual_intent=spec,
                    emotion=emotion,
                    provider=provider,
                    used_ids=used,
                    limit=5,
                    narrative_moment=narrative_moment,
                    style=style,
                    camera=camera,
                    avoid=avoid,
                    recent_selections=recent_selections,
                )

                for item in ranked:
                    url = item.get("url") or item.get("src", {}).get("original", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    score = score_asset(
                        query,
                        item,
                        media_type=media_type,
                        visual_intent=spec,
                        emotion=emotion,
                        provider=provider,
                        narrative_moment=narrative_moment,
                        style=style,
                        camera=camera,
                        avoid=avoid,
                        recent_selections=recent_selections,
                    )

                    min_threshold = MIN_PHOTO_RELEVANCE_SCORE if media_type == "photo" else MIN_RELEVANCE_SCORE
                    if score < min_threshold * 0.8:
                        continue

                    license_text = item.get("license") or item.get("credit") or ""
                    all_candidates.append({
                        "item": item,
                        "score": score,
                        "provider": provider,
                        "media_type": media_type,
                        "query": query,
                        "query_type": query_type,
                        "license_text": license_text,
                        "creator": item.get("credit") or item.get("photographer") or item.get("user", {}).get("name", ""),
                        "source_url": item.get("page_url") or item.get("url", ""),
                        "download_url": url,
                        "width": item.get("width", 0),
                        "height": item.get("height", 0),
                    })

    all_candidates.sort(key=lambda c: c["score"], reverse=True)

    # Deduplica por provider+id mantendo melhor score
    deduped: list[dict] = []
    seen_ids: set[str] = set()
    for candidate in all_candidates:
        item = candidate["item"]
        key = f"{candidate['provider']}:{item.get('id', candidate['download_url'])}"
        if key in seen_ids:
            continue
        seen_ids.add(key)
        deduped.append(candidate)

    return deduped[: max(min_candidates, 8)]
