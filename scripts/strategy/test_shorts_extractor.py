"""Testes para o extrator de Shorts."""

import unittest

from scripts.strategy.shorts_extractor import (
    _clip_ass_content,
    _format_ass_time,
    _parse_ass_time,
    _scene_emotional_weight,
    _select_best_scene,
)


class TestShortsExtractor(unittest.TestCase):
    def test_scene_emotional_weight_prefers_timeline(self):
        heavy = {
            "tipo": "hook",
            "timeline": {"scene_weight": 18.0, "intensity": 0.9},
        }
        light = {
            "tipo": "encerramento",
            "timeline": {"scene_weight": 6.0, "intensity": 0.2},
        }
        self.assertGreater(
            _scene_emotional_weight(heavy),
            _scene_emotional_weight(light),
        )

    def test_select_best_scene(self):
        scenes = [
            {"tipo": "hook", "tempo_inicio": 0, "tempo_fim": 5},
            {
                "tipo": "revelacao",
                "tempo_inicio": 5,
                "tempo_fim": 25,
                "timeline": {"scene_weight": 18.0, "section_key": "revelacao"},
            },
        ]
        best = _select_best_scene(scenes)
        self.assertEqual(best["tipo"], "revelacao")

    def test_ass_time_roundtrip(self):
        seconds = 125.47
        formatted = _format_ass_time(seconds)
        self.assertEqual(_parse_ass_time(formatted), 125.47)

    def test_clip_ass_rebases_timestamps(self):
        ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:02.00,0:00:05.00,Default,,0,0,0,,Antes
Dialogue: 0,0:00:10.00,0:00:15.00,Default,,0,0,0,,Durante
Dialogue: 0,0:00:20.00,0:00:25.00,Default,,0,0,0,,Depois
"""
        clipped = _clip_ass_content(ass, clip_start=10.0, clip_end=16.0)
        self.assertIn("PlayResX: 1080", clipped)
        self.assertIn("PlayResY: 1920", clipped)
        self.assertNotIn("Antes", clipped)
        self.assertIn("Durante", clipped)
        self.assertNotIn("Depois", clipped)
        self.assertIn("0:00:00.00", clipped)
        self.assertIn("0:00:05.00", clipped)


if __name__ == "__main__":
    unittest.main()
