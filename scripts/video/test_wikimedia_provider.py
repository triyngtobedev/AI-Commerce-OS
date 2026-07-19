"""Testes para Wikimedia Commons provider (sem rede real)."""

import unittest
from unittest.mock import MagicMock, patch

import requests

from scripts.video.media_providers.wikimedia_provider import search_wikimedia


class TestWikimediaProvider(unittest.TestCase):

    def _sample_search_response(self):
        return {
            "query": {
                "search": [
                    {"title": "File:Tunguska_event.jpg", "pageid": 1001},
                    {"title": "File:Small_thumb.jpg", "pageid": 1002},
                ],
            },
        }

    def _sample_imageinfo_response(self):
        return {
            "query": {
                "pages": [
                    {
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
                    {
                        "pageid": 1002,
                        "title": "File:Small_thumb.jpg",
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/small.jpg",
                            "width": 800,
                            "height": 600,
                            "extmetadata": {},
                        }],
                    },
                ],
            },
        }

    @patch("scripts.video.media_providers.wikimedia_provider._SESSION.get")
    def test_parses_valid_response(self, mock_get):
        search_response = MagicMock()
        search_response.raise_for_status = MagicMock()
        search_response.json.return_value = self._sample_search_response()

        info_response = MagicMock()
        info_response.raise_for_status = MagicMock()
        info_response.json.return_value = self._sample_imageinfo_response()

        mock_get.side_effect = [search_response, info_response]

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

    @patch("scripts.video.media_providers.wikimedia_provider._SESSION.get")
    def test_filters_low_resolution(self, mock_get):
        search_response = MagicMock()
        search_response.raise_for_status = MagicMock()
        search_response.json.return_value = {
            "query": {
                "search": [{"title": "File:Small_thumb.jpg", "pageid": 1002}],
            },
        }

        info_response = MagicMock()
        info_response.raise_for_status = MagicMock()
        info_response.json.return_value = {
            "query": {
                "pages": [self._sample_imageinfo_response()["query"]["pages"][1]],
            },
        }

        mock_get.side_effect = [search_response, info_response]

        result = search_wikimedia("small image")

        self.assertEqual(result["photos"], [])

    @patch("scripts.video.media_providers.wikimedia_provider._SESSION.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = TimeoutError("timeout")

        result = search_wikimedia("Tunguska")

        self.assertEqual(result, {"videos": [], "photos": []})

    @patch("scripts.video.media_providers.wikimedia_provider._SESSION.get")
    def test_http_error_returns_empty(self, mock_get):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("403")
        mock_get.return_value = response

        result = search_wikimedia("Tunguska")

        self.assertEqual(result, {"videos": [], "photos": []})


if __name__ == "__main__":
    unittest.main()
