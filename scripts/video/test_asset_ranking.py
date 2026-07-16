"""Testes para Asset Ranking — sem APIs reais."""

import unittest

from scripts.core.visual_intent_engine import VisualIntentSpec
from scripts.video.asset_ranking import (
    pick_best_asset,
    rank_assets,
    score_asset,
)


SAMPLE_VIDEOS = [
    {
        "id": "v1",
        "tags": ["historical", "documentary", "ancient", "ruins", "cinematic"],
        "url": "https://example.com/historical.mp4",
        "width": 1920,
        "height": 1080,
        "duration": 15,
    },
    {
        "id": "v2",
        "tags": ["gameplay", "minecraft", "gamer"],
        "url": "https://example.com/game.mp4",
        "width": 1280,
        "height": 720,
        "duration": 5,
    },
    {
        "id": "v3",
        "tags": ["ancient", "ruins", "mystery", "archive", "4k"],
        "url": "https://example.com/ruins.mp4",
        "width": 3840,
        "height": 2160,
        "duration": 20,
    },
]


class TestAssetRanking(unittest.TestCase):

    def test_scores_relevant_video_higher(self):
        spec = VisualIntentSpec(
            visual_intent="ancient_ruins",
            asset_priority=["historical_photo", "archive_video"],
            color_palette="cold",
            camera="zoom_in_center",
        )
        score_good = score_asset(
            "ancient ruins mystery",
            SAMPLE_VIDEOS[2],
            visual_intent=spec,
            emotion="mystery",
        )
        score_bad = score_asset(
            "ancient ruins mystery",
            SAMPLE_VIDEOS[1],
            visual_intent=spec,
            emotion="mystery",
        )
        self.assertGreater(score_good, score_bad)

    def test_rank_assets_orders_by_score(self):
        ranked = rank_assets(
            "ancient ruins documentary",
            SAMPLE_VIDEOS,
            emotion="mystery",
        )
        self.assertGreater(len(ranked), 0)
        scores = [score for _, score in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_pick_best_asset_skips_used_ids(self):
        best, score = pick_best_asset(
            "ancient ruins",
            SAMPLE_VIDEOS,
            used_ids={"v3"},
        )
        if best:
            self.assertNotEqual(best.get("id"), "v3")
        self.assertGreaterEqual(score, 0)

    def test_rejects_text_overlay_assets(self):
        video_with_text = {
            "id": "v4",
            "tags": ["documentary", "subtitle", "caption overlay"],
            "url": "https://example.com/text.mp4",
            "width": 1920,
            "height": 1080,
            "duration": 10,
        }
        score = score_asset("documentary", video_with_text)
        clean_score = score_asset("documentary", SAMPLE_VIDEOS[0])
        self.assertLessEqual(score, clean_score)


if __name__ == "__main__":
    unittest.main()
