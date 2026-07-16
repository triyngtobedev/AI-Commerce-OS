"""Testes rápidos do Media Engine e Renderer (sem FFmpeg/API)."""

import unittest

from scripts.video.media_downloader import (
    select_photo_url,
    select_video_file,
    select_video_file_with_fallback,
)
from scripts.video.media_providers.relevance import (
    MIN_ACCEPTABLE_QUALITY_SCORE,
    MIN_RELEVANCE_SCORE,
    best_video_score,
    pick_ranked_photos,
    pick_ranked_videos,
    score_video,
)
from scripts.video.scene_renderer import _video_motion_filter, _audio_delay
from scripts.video.scene_timeline import (
    _estimate_scene_durations,
    sync_scenes_to_audio,
)
from scripts.video.visual_media_engine import _enrich_search_query, _merge_media


class TestRelevance(unittest.TestCase):

    def _sample_video(self, **overrides):
        base = {
            "id": 1,
            "tags": ["siberian", "forest", "taiga"],
            "url": "https://example.com/siberian-forest",
            "user": {"name": "nature"},
            "width": 1920,
            "height": 1080,
            "duration": 18,
            "video_files": [
                {"quality": "hd", "width": 1920, "height": 1080, "link": "https://hd"},
                {"quality": "sd", "width": 640, "height": 360, "link": "https://sd"},
            ],
        }
        base.update(overrides)
        return base

    def test_relevant_video_passes_threshold(self):
        video = self._sample_video()
        score = score_video("remote siberian forest", video)
        self.assertGreaterEqual(score, MIN_RELEVANCE_SCORE)
        self.assertGreaterEqual(score, MIN_ACCEPTABLE_QUALITY_SCORE)
        self.assertEqual(len(pick_ranked_videos("remote siberian forest", [video], set())), 1)

    def test_gameplay_video_rejected(self):
        video = self._sample_video(
            id=3,
            tags=["gameplay", "minecraft", "gamer"],
            url="https://example.com/minecraft-gameplay",
        )
        self.assertEqual(score_video("siberian forest documentary", video), 0.0)
        self.assertEqual(
            pick_ranked_videos("siberian forest documentary", [video], set()),
            [],
        )

    def test_irrelevant_video_rejected(self):
        video = self._sample_video(
            id=2,
            tags=["coffee", "office"],
            url="https://example.com/office",
            duration=4,
        )
        self.assertEqual(
            pick_ranked_videos("remote siberian forest", [video], set()),
            [],
        )

    def test_select_video_file_prefers_1080p(self):
        video = self._sample_video()
        self.assertEqual(
            select_video_file(video),
            "https://hd",
        )

    def test_select_video_file_with_fallback(self):
        video = self._sample_video(
            video_files=[
                {"quality": "hd", "width": 1280, "height": 720, "link": "https://720"},
            ],
        )
        url, min_w, min_h = select_video_file_with_fallback(video)
        self.assertEqual(url, "https://720")
        self.assertEqual(min_w, 1280)


class TestMediaDownloader(unittest.TestCase):

    def test_select_photo_url_prefers_largest(self):
        photo = {
            "width": 4000,
            "height": 3000,
            "src": {
                "original": "https://example.com/original.jpg",
                "medium": "https://example.com/medium.jpg",
            },
        }
        self.assertEqual(select_photo_url(photo), "https://example.com/original.jpg")


class TestSceneTimeline(unittest.TestCase):

    def test_estimate_scene_durations_uses_scene_narration(self):
        scenes = [
            {"tipo": "hook", "narracao": " ".join(["curta"] * 20)},
            {"tipo": "contexto", "narracao": " ".join(["longa"] * 120)},
        ]
        durations = _estimate_scene_durations(scenes, "", 100.0)

        self.assertEqual(len(durations), 2)
        self.assertGreater(durations[1], durations[0])
        self.assertAlmostEqual(sum(durations), 100.0, delta=0.1)

    def test_sync_preserves_per_scene_narration(self):
        scenes = {
            "cenas": [
                {"tipo": "hook", "narracao": "texto hook", "visual": "a"},
                {"tipo": "contexto", "narracao": "texto contexto", "visual": "b"},
            ],
        }
        result = sync_scenes_to_audio(scenes, "fallback global", "/missing/audio.mp3")

        self.assertEqual(result["cenas"][0]["narracao"], "texto hook")
        self.assertEqual(result["cenas"][1]["narracao"], "texto contexto")


class TestRendererFilters(unittest.TestCase):

    def test_video_motion_filter_varies_by_scene(self):
        first = _video_motion_filter(1920, 1080, 10.0, 0, motion="subtle")
        second = _video_motion_filter(1920, 1080, 10.0, 1, motion="subtle")
        self.assertNotEqual(first, second)
        self.assertIn("crop=1920:1080", first)
        self.assertIn("fps=30", first)

    def test_audio_delay_for_youtube_dark(self):
        delay = _audio_delay("youtube_dark")
        self.assertGreater(delay, 0.0)


class TestVisualMediaEngine(unittest.TestCase):

    def test_enrich_search_query_adds_cinematic_suffix(self):
        queries = _enrich_search_query(
            "siberian taiga aerial",
            "contexto",
            "historical documentary",
        )
        self.assertGreater(len(queries), 1)
        self.assertTrue(any("cinematic" in q for q in queries))

    def test_merge_media_deduplicates_ids(self):
        target = {"videos": [{"id": 1, "width": 1920}], "photos": []}
        source = {
            "videos": [{"id": 1, "width": 1920}, {"id": 2, "width": 1920}],
            "photos": [{"id": 10, "width": 2000}],
        }
        _merge_media(target, source)
        self.assertEqual(len(target["videos"]), 2)
        self.assertEqual(len(target["photos"]), 1)

    def test_best_video_score_empty(self):
        self.assertEqual(best_video_score("forest", [], set()), 0.0)


if __name__ == "__main__":
    unittest.main()
