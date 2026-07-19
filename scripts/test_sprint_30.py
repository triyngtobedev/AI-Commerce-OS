"""Testes Sprint 30 — Visual Intelligence & Editorial Quality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.scoring.visual_relevance_scorer import (
    compute_final_score,
    rank_candidates_with_visual_score,
    scene_hash,
)
from scripts.youtube.retention_analyzer import analyze_retention
from scripts.youtube.retention_controller import (
    apply_retention_actions,
    generate_retention_actions,
    run_retention_controller,
)
from scripts.youtube.thumbnail_scorer import score_thumbnail
from scripts.audio.audio_layer import (
    build_sfx_timeline,
    select_track_for_act,
    _act_boundaries,
)


class TestVisualRelevanceScorer(unittest.TestCase):

    def test_compute_final_score_weights(self):
        scores = {
            "conceptual_match": 80,
            "literal_match": 70,
            "visual_quality": 90,
            "on_brand_documentary": 85,
            "hard_penalty_reasons": [],
        }
        final = compute_final_score(scores)
        expected = 0.4 * 80 + 0.25 * 70 + 0.2 * 90 + 0.15 * 85
        self.assertAlmostEqual(final, expected, places=1)

    def test_hard_penalty_applied(self):
        scores = {
            "conceptual_match": 80,
            "literal_match": 70,
            "visual_quality": 90,
            "on_brand_documentary": 85,
            "hard_penalty_reasons": ["watermark"],
        }
        final = compute_final_score(scores)
        self.assertLess(final, 70)

    def test_scene_hash_deterministic(self):
        scene = {"tipo": "hook", "narracao": "test phrase"}
        self.assertEqual(scene_hash(scene), scene_hash(scene))

    def test_rank_candidates_heuristic_fallback(self):
        scene = {"tipo": "hook", "narracao": "ancient ruins mystery"}
        candidates = [
            {
                "item": {"id": "1", "tags": ["ancient", "ruins"], "width": 1920, "height": 1080},
                "provider": "pexels",
                "media_type": "video",
                "score": 0.7,
            },
            {
                "item": {"id": "2", "tags": ["gameplay"], "width": 1920, "height": 1080},
                "provider": "pexels",
                "media_type": "video",
                "score": 0.8,
            },
        ]
        ranked = rank_candidates_with_visual_score(
            candidates, scene, use_cache=False,
        )
        self.assertEqual(len(ranked), 2)
        self.assertIn("visual_score", ranked[0])


class TestRetentionController(unittest.TestCase):

    def test_max_three_actions(self):
        report = analyze_retention({
            "hook": "Fraco.",
            "desenvolvimento": "x " * 400,
            "revelacao": "Curto.",
            "contexto": "c",
            "consequencias": "c",
            "encerramento": "c",
        })
        scenes = {
            "cenas": [
                {"tipo": "hook", "narracao": "h", "duration": 10},
                {"tipo": "contexto", "narracao": "c", "duration": 10},
                {"tipo": "desenvolvimento_1", "narracao": "d", "duration": 25},
                {"tipo": "desenvolvimento_2", "narracao": "d2", "duration": 25},
                {"tipo": "revelacao", "narracao": "r", "duration": 10},
                {"tipo": "consequencias", "narracao": "c2", "duration": 10},
                {"tipo": "impacto", "narracao": "i", "duration": 10},
                {"tipo": "encerramento", "narracao": "e", "duration": 10},
            ]
        }
        actions = generate_retention_actions(report, scenes)
        self.assertLessEqual(len(actions["actions"]), 3)

    def test_cut_scene_blocks_critical(self):
        scenes = {
            "cenas": [
                {"tipo": "hook", "narracao": "h", "critical": True},
                {"tipo": "contexto", "narracao": "c"},
            ]
        }
        payload = {"actions": [{"type": "cut_scene", "index": 0, "reason": "test"}]}
        updated, applied = apply_retention_actions(scenes, payload)
        self.assertFalse(applied[0]["applied"])
        self.assertEqual(len(updated["cenas"]), 2)

    def test_run_retention_controller_writes_json(self):
        scenes = {"cenas": [{"tipo": "hook", "narracao": "h"}]}
        report = {"hook_strength": 40, "slow_scenes": [], "repetitions": []}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_retention_controller(
                scenes,
                retention_report=report,
                output_dir=out,
            )
            self.assertTrue((out / "retention_actions.json").exists())


class TestAudioLayer(unittest.TestCase):

    def test_select_track_avoids_empty(self):
        track = select_track_for_act(2, topic="test topic hash")
        self.assertIn("mood", track)

    def test_sfx_whoosh_on_scene_changes(self):
        scenes = {
            "cenas": [
                {"tipo": "hook", "start_time": 0},
                {"tipo": "contexto", "start_time": 15},
                {"tipo": "revelacao", "start_time": 120},
            ]
        }
        events = build_sfx_timeline(scenes)
        whoosh = [e for e in events if e["sfx"] == "whoosh"]
        self.assertGreaterEqual(len(whoosh), 2)

    def test_act_boundaries(self):
        bounds = _act_boundaries(8)
        self.assertIn(8, bounds)


class TestThumbnailScorer(unittest.TestCase):

    def test_heuristic_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "thumb.jpg"
            # Minimal valid JPEG header bytes
            path.write_bytes(
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xd9"
            )
            scores = score_thumbnail(path, title="Test", variant="A", concept="Tensão")
            self.assertIn("composite_score", scores)
            self.assertGreater(scores["composite_score"], 0)


if __name__ == "__main__":
    unittest.main()
