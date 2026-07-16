"""Testes para timeline de cenas."""

import unittest

from scripts.video.scene_timeline import (
    sync_scenes_to_audio,
    _split_text_by_weights,
    _estimate_scene_durations,
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
        self.assertEqual(len(cenas), 2)
        self.assertIn("duration_seconds", cenas[0])
        self.assertIn("tempo_inicio", cenas[0])

    def test_scene_weights_defined(self):
        self.assertIn("hook", SCENE_WEIGHTS)
        self.assertIn("encerramento", SCENE_WEIGHTS)


if __name__ == "__main__":
    unittest.main()
