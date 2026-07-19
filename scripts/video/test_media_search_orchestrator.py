"""Testes do Media Search Orchestrator."""

from scripts.video.media_search_orchestrator import (
    generate_scene_queries,
    QUERY_TYPES,
)


def test_generate_scene_queries_has_required_types():
    scene = {
        "visual": "textile factory production line",
        "tipo": "desenvolvimento_1",
        "emotion": "tension",
        "must_show": "garment workers sewing",
    }
    queries = generate_scene_queries(scene, topic="Shein fast fashion")

    for qtype in ("factual", "visual", "emotional", "historical", "symbolic", "alt_en", "alt_pt"):
        assert qtype in queries
        assert queries[qtype]


def test_generate_scene_queries_english_localized():
    scene = {
        "visual": "fábrica têxtil acelerada",
        "tipo": "hook",
        "emotion": "impact",
    }
    queries = generate_scene_queries(scene, topic="Como a Shein ficou poderosa")
    assert queries["alt_en"]
    assert "documentary" in queries["historical"].lower() or "historical" in queries["historical"]


def test_query_types_constant():
    assert len(QUERY_TYPES) >= 7
