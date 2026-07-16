"""Testes para Wikimedia Commons provider (sem rede real)."""

import unittest
from unittest.mock import MagicMock, patch

from scripts.video.wikimedia_provider import search_wikimedia


class TestWikimediaProvider(unittest.TestCase):

    def _sample_api_response(self):
        return {
            "query": {
                "pages": {
                    "1001": {
                        "pageid": 1001,
                        "title": "File:Tunguska_event.jpg",
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/tunguska.jpg",
                            "width": 2000,
                            "height": 1500,
                            "extmetadata": {
                                "Artist": {"value": "Public Domain"},
                                "LicenseShortName": {"value": "PD"},
                            },
                        }],
                    },
                    "1002": {
                        "pageid": 1002,
                        "title": "File:Small_thumb.jpg",
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/small.jpg",
                            "width": 800,
                            "height": 600,
                            "extmetadata": {},
                        }],
                    },
                },
            },
        }

    @patch("scripts.video.wikimedia_provider.requests.get")
    def test_parses_valid_response(self, mock_get):
        response = MagicMock()
        response.ok = True
        response.json.return_value = self._sample_api_response()
        mock_get.return_value = response

        result = search_wikimedia("Tunguska event")

        self.assertEqual(result["videos"], [])
        self.assertEqual(len(result["photos"]), 1)
        photo = result["photos"][0]
        self.assertEqual(photo["id"], 1001)
        self.assertEqual(
            photo["src"]["original"],
            "https://upload.wikimedia.org/tunguska.jpg",
        )
        self.assertIn("Public Domain", photo["credit"])

    @patch("scripts.video.wikimedia_provider.requests.get")
    def test_filters_low_resolution(self, mock_get):
        response = MagicMock()
        response.ok = True
        response.json.return_value = {
            "query": {
                "pages": {
                    "1002": self._sample_api_response()["query"]["pages"]["1002"],
                },
            },
        }
        mock_get.return_value = response

        result = search_wikimedia("small image")

        self.assertEqual(result["photos"], [])

    @patch("scripts.video.wikimedia_provider.requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = TimeoutError("timeout")

        result = search_wikimedia("Tunguska")

        self.assertEqual(result, {"videos": [], "photos": []})

    @patch("scripts.video.wikimedia_provider.requests.get")
    def test_http_error_returns_empty(self, mock_get):
        response = MagicMock()
        response.ok = False
        mock_get.return_value = response

        result = search_wikimedia("Tunguska")

        self.assertEqual(result, {"videos": [], "photos": []})


if __name__ == "__main__":
    unittest.main()
