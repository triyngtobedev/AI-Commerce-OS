"""Testes do localizador de queries para busca de mídia YouTube."""

from scripts.video.query_localizer import (
    CRITICAL_SCENE_TIPOS,
    is_critical_scene,
    localize_search_query,
    looks_portuguese,
    should_prioritize_wikimedia,
    wikimedia_query_variants,
)


def test_localize_portuguese_war_query() -> None:
    query = "Operação Barbarossa invasão da União Soviética 1941"
    result = localize_search_query(query)
    assert "operation barbarossa" in result.lower()
    assert "invasion" in result.lower()
    assert looks_portuguese(query)


def test_localize_preserves_english_query() -> None:
    query = "world war ii eastern front documentary aerial"
    assert localize_search_query(query) == query
    assert not looks_portuguese(query)


def test_critical_scene_detection() -> None:
    assert is_critical_scene("hook")
    assert is_critical_scene("revelacao")
    assert is_critical_scene("encerramento")
    assert not is_critical_scene("contexto")
    assert len(CRITICAL_SCENE_TIPOS) == 3


def test_wikimedia_priority_for_historical_intent() -> None:
    item = {
        "visual_intent": "historical_event",
        "primary_asset": "archive_video",
    }
    assert should_prioritize_wikimedia(item)


def test_wikimedia_query_variants_include_map() -> None:
    item = {
        "primary_asset": "old_map",
        "visual_direction": {"primary_asset": "old_map"},
    }
    variants = wikimedia_query_variants("fronte oriental 1942", item)
    assert any("map" in variant for variant in variants)
