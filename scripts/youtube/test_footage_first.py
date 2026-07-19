"""Testes do Scene Visual Planner e Retention Analyzer."""

from scripts.youtube.scene_visual_planner import enrich_scene_visual_plan, enrich_scenes_with_visual_plan
from scripts.youtube.retention_analyzer import analyze_retention, RetentionReport


def test_enrich_scene_has_visual_fields():
    scene = {"tipo": "hook", "visual": "Shein warehouse logistics"}
    enriched = enrich_scene_visual_plan(scene, topic="Como a Shein ficou poderosa")

    assert enriched.get("scene_type") == "hook"
    assert enriched.get("must_show")
    assert enriched.get("asset_queries")
    assert enriched.get("fallback_visual_plan")
    assert enriched.get("avoid_showing")


def test_enrich_all_scenes():
    scenes = {
        "produto": "Shein",
        "cenas": [
            {"tipo": "hook", "visual": "factory"},
            {"tipo": "contexto", "visual": "map china"},
        ],
    }
    result = enrich_scenes_with_visual_plan(scenes, topic="Shein")
    assert result["visual_plan_version"] == 2
    assert all("asset_queries" in c for c in result["cenas"])


def test_retention_analyzes_hook():
    script = {
        "hook": "Em 2020, a Shein vendeu mais que a Zara. Como?",
        "contexto": "A moda rápida mudou para sempre.",
        "desenvolvimento": "Mas espere — tem mais. " * 50,
        "revelacao": "O segredo estava na logística invisível.",
        "consequencias": "E isso mudou o comércio global.",
        "encerramento": "Inscreva-se para mais histórias.",
    }
    report = analyze_retention(script)
    assert isinstance(report, RetentionReport)
    assert report.hook_strength > 50
    assert report.overall_score > 0
