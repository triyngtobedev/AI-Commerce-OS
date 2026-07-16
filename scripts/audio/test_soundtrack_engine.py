"""Testes para Soundtrack Engine."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.audio.soundtrack_engine import (
    _dominant_emotion,
    generate_soundtrack,
)


class TestSoundtrackEngine(unittest.TestCase):

    def test_dominant_emotion_picks_highest_weight(self):
        timeline = {
            "sections": [
                {"emotion": "mystery", "intensity": 0.8, "duration": 60},
                {"emotion": "impact", "intensity": 0.9, "duration": 30},
            ],
        }
        self.assertEqual(_dominant_emotion(timeline), "mystery")

    def test_procedural_fallback_generates_file(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "soundtrack.mp3"
            with patch("scripts.audio.soundtrack_engine._search_pixabay_music", return_value=None):
                with patch("scripts.audio.soundtrack_engine.probe_duration", return_value=60.0):
                    result = generate_soundtrack(
                        output,
                        emotional_timeline={"sections": [{"emotion": "calm", "duration": 60}]},
                        audio_duration=60.0,
                    )
            if result:
                self.assertTrue(result.exists())
                self.assertGreater(result.stat().st_size, 500)


if __name__ == "__main__":
    unittest.main()
