"""Testes para Pixabay provider (sem rede real)."""

import unittest
from unittest.mock import MagicMock, patch

import scripts.video.pixabay_provider as pixabay_module
from scripts.video.pixabay_provider import search_pixabay


class TestPixabayProvider(unittest.TestCase):

    def setUp(self):
        pixabay_module._WARNED_NO_KEY = False

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_api_key_returns_empty(self):
        result = search_pixabay("forest")

        self.assertEqual(result, {"videos": [], "photos": []})

    @patch.dict("os.environ", {"PIXABAY_API_KEY": "test-key"})
    @patch("scripts.video.pixabay_provider.requests.get")
    def test_parses_video_response(self, mock_get):
        video_response = MagicMock()
        video_response.ok = True
        video_response.json.return_value = {
            "hits": [{
                "id": 42,
                "duration": 12,
                "tags": "forest, nature",
                "pageURL": "https://pixabay.com/videos/42",
                "videos": {
                    "large": {
                        "url": "https://cdn.pixabay.com/large.mp4",
                        "width": 1920,
                        "height": 1080,
                    },
                },
            }],
        }
        mock_get.return_value = video_response

        result = search_pixabay("forest")

        self.assertEqual(len(result["videos"]), 1)
        self.assertEqual(result["videos"][0]["id"], 42)
        self.assertEqual(
            result["videos"][0]["video_files"][0]["link"],
            "https://cdn.pixabay.com/large.mp4",
        )
        self.assertEqual(result["photos"], [])

    @patch.dict("os.environ", {"PIXABAY_API_KEY": "test-key"})
    @patch("scripts.video.pixabay_provider.requests.get")
    def test_falls_back_to_photos_when_no_videos(self, mock_get):
        empty_videos = MagicMock()
        empty_videos.ok = True
        empty_videos.json.return_value = {"hits": []}

        photo_response = MagicMock()
        photo_response.ok = True
        photo_response.json.return_value = {
            "hits": [{
                "id": 99,
                "imageWidth": 3000,
                "imageHeight": 2000,
                "tags": "history",
                "pageURL": "https://pixabay.com/photos/99",
                "user": "author",
                "largeImageURL": "https://cdn.pixabay.com/large.jpg",
                "webformatURL": "https://cdn.pixabay.com/web.jpg",
            }],
        }

        mock_get.side_effect = [empty_videos, photo_response]

        result = search_pixabay("history")

        self.assertEqual(result["videos"], [])
        self.assertEqual(len(result["photos"]), 1)
        self.assertEqual(
            result["photos"][0]["src"]["original"],
            "https://cdn.pixabay.com/large.jpg",
        )

    @patch.dict("os.environ", {"PIXABAY_API_KEY": "test-key"})
    @patch("scripts.video.pixabay_provider.requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = ConnectionError("offline")

        result = search_pixabay("forest")

        self.assertEqual(result["videos"], [])
        self.assertEqual(result["photos"], [])


if __name__ == "__main__":
    unittest.main()
