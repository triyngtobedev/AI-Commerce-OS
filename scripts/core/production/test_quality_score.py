"""Testes para Quality Score."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.core.production.quality_score import (
    MIN_QUALITY_SCORE,
    run_quality_score,
)


class TestQualityScore(unittest.TestCase):

    def _minimal_result(self):
        return {
            "cenas": {
                "cenas": [
                    {"tipo": "hook", "duration_seconds": 30, "scene_motion": "zoom_in_center"},
                    {"tipo": "contexto", "duration_seconds": 45, "scene_motion": "parallax_left"},
                ],
                "audio_duration": 75.0,
                "synced": True,
            },
            "audio": "assets/audio/narracao.mp3",
            "youtube_metadata": {},
        }

    def test_fails_without_artifacts(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = run_quality_score(folder, self._minimal_result(), min_score=70)
            self.assertFalse(report.passed)
            self.assertLess(report.score, 70)

    def test_passes_with_complete_package(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            assets = folder / "assets"
            audio_dir = assets / "audio"
            audio_dir.mkdir(parents=True)
            (audio_dir / "narracao.mp3").write_bytes(b"\x00" * 2000)
            (audio_dir / "soundtrack.mp3").write_bytes(b"\x00" * 2000)

            (folder / "captions.srt").write_text(
                "1\n00:00:00,000 --> 00:00:05,000\nTexto curto.\n\n"
                "2\n00:00:05,100 --> 00:01:15,000\nSegunda frase.\n",
                encoding="utf-8",
            )

            (assets / "media_search.json").write_text(json.dumps({
                "scenes": [
                    {"saved": True, "quality_score": 0.7, "media_type": "video"},
                    {"saved": True, "quality_score": 0.65, "media_type": "video"},
                ],
            }), encoding="utf-8")

            (assets / "videos").mkdir()
            (assets / "images").mkdir()
            (assets / "videos" / "scene-01.mp4").write_bytes(b"\x00")
            (assets / "videos" / "scene-02.mp4").write_bytes(b"\x00")

            with patch("scripts.core.production.quality_score.probe_duration", return_value=75.0):
                with patch("scripts.core.production.quality_score._probe_video", return_value={
                    "streams": [{"codec_type": "video"}, {"codec_type": "audio"}],
                    "format": {"duration": "75.0"},
                }):
                    with patch("scripts.core.production.quality_score.score_image_contrast", return_value=55.0):
                        report = run_quality_score(folder, self._minimal_result(), min_score=50)
                        self.assertTrue(report.passed)
                        self.assertGreaterEqual(report.score, 50)

    def test_min_score_constant(self):
        self.assertEqual(MIN_QUALITY_SCORE, 70.0)


if __name__ == "__main__":
    unittest.main()
