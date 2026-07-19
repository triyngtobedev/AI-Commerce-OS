"""Testes para timeline de cenas."""

import unittest
from unittest.mock import patch

from scripts.core.emotional_timeline import EmotionalTimeline, TimelineSection
from scripts.video.scene_emotion import apply_timeline_to_scenes
from scripts.video.scene_timeline import (
    sync_scenes_to_audio,
    split_long_scenes,
    normalize_scene_list,
    _split_text_by_weights,
    _split_narration_at_sentences,
    SCENE_WEIGHTS,
)


class TestSceneTimeline(unittest.TestCase):

    def test_split_text_by_weights(self):
        text = " ".join([f"w{i}" for i in range(100)])
        weights = [10, 20, 30, 40]
        chunks = _split_text_by_weights(text, weights)

        self.assertEqual(len(chunks), 4)
        total_words = sum(len(c.split()) for c in chunks)
        self.assertEqual(total_words, 100)

    def test_sync_scenes_estimates_when_no_audio(self):
        scenes = {
            "cenas": [
                {"tipo": "hook", "visual": "test"},
                {"tipo": "contexto", "visual": "test2"},
            ],
        }
        narracao = " ".join(["palavra"] * 300)

        result = sync_scenes_to_audio(
            scenes,
            narracao,
            "/nonexistent/audio.mp3",
        )

        self.assertTrue(result.get("synced"))
        self.assertGreater(result.get("audio_duration", 0), 0)

        cenas = result["cenas"]
        self.assertGreaterEqual(len(cenas), 2)
        for scene in cenas:
            self.assertIn("duration_seconds", scene)
            self.assertIn("tempo_inicio", scene)
            self.assertLessEqual(scene["duration_seconds"], 20.0)

    def test_scene_weights_defined(self):
        self.assertIn("hook", SCENE_WEIGHTS)
        self.assertIn("encerramento", SCENE_WEIGHTS)

    def test_split_narration_at_sentences(self):
        text = "Primeira frase longa aqui. Segunda frase também. Terceira frase final."
        parts = _split_narration_at_sentences(text, 2)
        self.assertEqual(len(parts), 2)
        self.assertIn(".", parts[0])

    def test_normalize_scene_list_from_section_dict(self):
        raw = {
            "gancho": "Texto do gancho.",
            "contexto": "Texto do contexto.",
        }
        normalized = normalize_scene_list(raw, section_order=["gancho", "contexto"])
        self.assertEqual(len(normalized), 2)
        self.assertIsInstance(normalized[0], dict)
        self.assertEqual(normalized[0]["tipo"], "gancho")
        self.assertEqual(normalized[0]["narracao"], "Texto do gancho.")

    def test_split_long_scenes_skips_documentario_8cenas(self):
        scenes = {
            "roteiro_template": "documentario_8cenas",
            "cenas": [{
                "tipo": "revelacao",
                "narracao": " ".join(["Palavra"] * 200),
                "duration_seconds": 90.0,
                "tempo_inicio": 0.0,
                "tempo_fim": 90.0,
            }],
            "audio_duration": 90.0,
        }
        result = split_long_scenes(scenes)
        self.assertEqual(len(result["cenas"]), 1)
        self.assertEqual(result["cenas"][0]["duration_seconds"], 90.0)

    def test_split_long_scenes_divides_above_20s(self):
        scenes = {
            "cenas": [{
                "tipo": "revelacao",
                "narracao": "Frase um longa. Frase dois longa. Frase três longa. Frase quatro longa.",
                "duration_seconds": 90.0,
                "tempo_inicio": 0.0,
                "tempo_fim": 90.0,
            }],
            "audio_duration": 90.0,
        }
        result = split_long_scenes(scenes)
        expanded = result["cenas"]
        self.assertGreater(len(expanded), 1)
        for scene in expanded:
            self.assertLessEqual(scene["duration_seconds"], 20.0)
        self.assertEqual(expanded[0].get("media_index"), 0)

    @patch("scripts.video.scene_timeline.probe_duration", return_value=120.0)
    def test_sync_splits_long_scenes_with_audio(self, _mock_probe):
        scenes = {
            "cenas": [
                {"tipo": "hook", "narracao": "Hook curto."},
                {"tipo": "revelacao", "narracao": " ".join(["Palavra"] * 200)},
            ],
        }
        result = sync_scenes_to_audio(scenes, " ".join(["Palavra"] * 210), "/fake/audio.mp3")
        durations = [s["duration_seconds"] for s in result["cenas"]]
        self.assertTrue(all(d <= 20.0 for d in durations[:-1] or durations))

    def test_apply_timeline_assigns_duration_for_unmatched_scene_types(self):
        timeline = EmotionalTimeline(
            sections=[
                TimelineSection(
                    text="Hook",
                    emotion="impact",
                    intensity=0.9,
                    section_key="hook",
                    real_duration=10.0,
                    duration=10.0,
                ),
                TimelineSection(
                    text="Fato 5",
                    emotion="mystery",
                    intensity=0.6,
                    section_key="fato_5",
                    real_duration=20.0,
                    duration=20.0,
                ),
            ],
            total_duration=30.0,
            director_meta={"synced_to_audio": True},
        )
        scenes = {
            "cenas": [
                {"tipo": "hook", "narracao": "Hook."},
                {"tipo": "desenvolvimento_1", "narracao": "Legado sem match."},
            ],
            "synced": True,
        }

        result = apply_timeline_to_scenes(scenes, timeline)

        for scene in result["cenas"]:
            self.assertGreater(float(scene.get("duration_seconds", 0)), 0)


if __name__ == "__main__":
    unittest.main()
