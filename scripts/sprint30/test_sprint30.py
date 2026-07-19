"""Testes Sprint 30 — flags, métricas e retention."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class TestSprint30Config(unittest.TestCase):
    @patch.dict(os.environ, {"SPRINT30": "true", "FOOTAGE_FIRST": "true", "RETENTION_CONTROLLER": "false"})
    def test_flags_when_sprint30_enabled(self):
        from scripts.sprint30.config import get_flags, is_footage_first, is_retention_controller_enabled

        self.assertTrue(is_footage_first())
        self.assertFalse(is_retention_controller_enabled())
        flags = get_flags()
        self.assertTrue(flags["SPRINT30"])
        self.assertTrue(flags["FOOTAGE_FIRST"])
        self.assertFalse(flags["RETENTION_CONTROLLER"])

    @patch.dict(os.environ, {"SPRINT30": "false", "FOOTAGE_FIRST": "true"}, clear=False)
    def test_footage_first_requires_sprint30(self):
        from scripts.sprint30.config import is_footage_first

        self.assertFalse(is_footage_first())


class TestSprint30Metrics(unittest.TestCase):
    def test_append_and_summarize(self):
        from scripts.sprint30.metrics import append_sprint30_metrics, set_batch_id, summarize_metrics_file

        with tempfile.TemporaryDirectory() as tmp:
            metrics_path = Path(tmp) / "sprint_30_metrics.jsonl"
            set_batch_id("test-batch-001")

            with patch.dict(os.environ, {"SPRINT30_METRICS_PATH": str(metrics_path)}):
                append_sprint30_metrics(
                    {
                        "batch_id": "test-batch-001",
                        "status": "completed",
                        "visual_relevance_avg": 0.72,
                        "thumbnail_ctr_estimate": 0.65,
                        "retention_predicted_score": 68.0,
                        "audio_layer_adequate": True,
                        "audio_sfx_count": 2,
                        "retention_actions_count": 1,
                    }
                )
                summary = summarize_metrics_file(metrics_path)

            self.assertEqual(summary["completed"], 1)
            self.assertEqual(summary["visual_relevance_avg"], 0.72)
            self.assertEqual(summary["retention_predicted_score_avg"], 68.0)


class TestRetentionController(unittest.TestCase):
    def test_hook_boost_adds_actions(self):
        from scripts.sprint30.retention_controller import apply_retention_optimizations

        scenes = {
            "cenas": [
                {"tipo": "hook", "duration_seconds": 12},
                {"tipo": "desenvolvimento_1", "duration_seconds": 18},
            ]
        }
        timeline = {"sections": [{"emotion": "mystery", "intensity": 0.7}]}

        with patch.dict(os.environ, {"SPRINT30": "true", "RETENTION_CONTROLLER": "true"}):
            updated = apply_retention_optimizations(scenes, timeline)

        self.assertIn("retention_actions", updated)
        self.assertTrue(updated["retention_actions"])


class TestRouterHealth(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "test-key",
            "PEXELS_API_KEY": "test-key",
            "SPRINT30": "true",
            "FOOTAGE_FIRST": "true",
            "RETENTION_CONTROLLER": "true",
        },
        clear=False,
    )
    @patch("shutil.which", return_value="/usr/bin/ffmpeg")
    def test_health_ready_shape(self, _mock_which):
        from scripts.ai.router import get_client

        health = get_client().health()
        self.assertIn("ready_for_batch", health)
        self.assertIn("flags", health)
        self.assertIn("tts", health)
        self.assertIn("ai", health)
        self.assertTrue(health["flags"]["SPRINT30"])
        self.assertEqual(health["ai"]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
