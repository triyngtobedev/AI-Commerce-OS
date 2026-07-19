"""Testes da Visual Grammar."""

from scripts.video.visual_grammar import (
    resolve_editorial_scene_type,
    get_visual_grammar,
    apply_visual_grammar_to_scene,
    apply_visual_grammar_to_scenes,
)


def test_legacy_type_mapping():
    assert resolve_editorial_scene_type({"tipo": "hook"}) == "hook"
    assert resolve_editorial_scene_type({"tipo": "revelacao"}) == "turning_point"
    assert resolve_editorial_scene_type({"tipo": "impacto"}) == "data"


def test_explicit_scene_type():
    assert resolve_editorial_scene_type({"scene_type": "timeline"}) == "timeline"


def test_hook_grammar_aggressive():
    spec = get_visual_grammar({"tipo": "hook"})
    assert spec.cut_pace == "fast"
    assert spec.zoom_intensity >= 1.2
    assert spec.overlay_type == "headline"


def test_data_grammar_motion_graphics():
    spec = get_visual_grammar({"scene_type": "data"})
    assert spec.overlay_type == "data"
    assert spec.ken_burns is False


def test_apply_to_scenes():
    scenes = {
        "produto": "Shein",
        "cenas": [
            {"tipo": "hook", "visual": "factory"},
            {"tipo": "contexto", "visual": "map"},
        ],
    }
    result = apply_visual_grammar_to_scenes(scenes)
    assert result["cenas"][0]["visual_grammar"]["cut_pace"] == "fast"
    assert "scene_motion" in result["cenas"][0]
