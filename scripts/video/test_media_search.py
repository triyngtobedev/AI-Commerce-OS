"""Testes para media_search e asset queries (sem rede real)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.video.asset_search import generate_asset_queries
from scripts.video.media_search import search_media


class TestMediaSearch(unittest.TestCase):

    def _subject(self, platform="youtube_dark"):
        return {
            "nome": "Teste Tunguska",
            "slug": "teste-tunguska",
            "_output_platform": platform,
        }

    def _queries(self):
        return [{
            "busca": "Tunguska explosion 1908",
            "busca_fallback": "historical documentary cinematic",
            "tipo": "contexto",
            "tempo": "30-90",
        }]

    @patch("scripts.video.media_search.search_pexels")
    @patch("scripts.video.media_search.search_pixabay")
    @patch("scripts.video.media_search.search_wikimedia")
    def test_youtube_dark_tries_wikimedia_first(
        self,
        mock_wikimedia,
        mock_pixabay,
        mock_pexels,
    ):
        mock_wikimedia.return_value = {
            "photos": [{"id": 1, "src": {"original": "https://wm.org/a.jpg"}}],
            "videos": [],
        }
        mock_pixabay.return_value = {"photos": [], "videos": []}
        mock_pexels.return_value = {"photos": [], "videos": []}

        with tempfile.TemporaryDirectory() as tmp:
            subject = self._subject("youtube_dark")
            subject["slug"] = Path(tmp).name

            with patch(
                "scripts.video.media_search.content_output_dir",
                return_value=Path(tmp),
            ):
                output = search_media(subject, self._queries())

        self.assertEqual(output["assets"][0]["provedor"], "wikimedia")
        mock_wikimedia.assert_called_once()
        mock_pixabay.assert_not_called()
        mock_pexels.assert_not_called()

    @patch("scripts.video.media_search.search_pexels")
    @patch("scripts.video.media_search.search_pixabay")
    @patch("scripts.video.media_search.search_wikimedia")
    def test_youtube_dark_falls_back_to_pixabay_then_pexels(
        self,
        mock_wikimedia,
        mock_pixabay,
        mock_pexels,
    ):
        mock_wikimedia.return_value = {"photos": [], "videos": []}
        mock_pixabay.return_value = {"photos": [], "videos": []}
        mock_pexels.return_value = {
            "videos": [{"id": 10, "video_files": []}],
            "photos": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            subject = self._subject("youtube_dark")

            with patch(
                "scripts.video.media_search.content_output_dir",
                return_value=Path(tmp),
            ):
                output = search_media(subject, self._queries())

        self.assertEqual(output["assets"][0]["provedor"], "pexels")
        mock_wikimedia.assert_called_once()
        mock_pixabay.assert_called_once()
        mock_pexels.assert_called_once()

    @patch("scripts.video.media_search.search_pexels")
    @patch("scripts.video.media_search.search_pixabay")
    @patch("scripts.video.media_search.search_wikimedia")
    def test_tiktok_shop_only_uses_pexels(
        self,
        mock_wikimedia,
        mock_pixabay,
        mock_pexels,
    ):
        mock_pexels.return_value = {
            "videos": [{"id": 5, "video_files": []}],
            "photos": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            subject = self._subject("tiktok_shop")

            with patch(
                "scripts.video.media_search.content_output_dir",
                return_value=Path(tmp),
            ):
                output = search_media(subject, self._queries())

        mock_wikimedia.assert_not_called()
        mock_pixabay.assert_not_called()
        mock_pexels.assert_called_once()
        self.assertEqual(output["assets"][0]["provedor"], "pexels")


class TestAssetQueries(unittest.TestCase):

    def test_preferir_imagem_for_youtube_documentary_scenes(self):
        scenes = {
            "angulo": "misterio_nao_resolvido",
            "produto": "Tunguska",
            "cenas": [
                {"tipo": "hook", "visual": "explosion", "tempo": "0-30"},
                {"tipo": "contexto", "visual": "siberia map", "tempo": "30-90"},
                {"tipo": "encerramento", "visual": "closing", "tempo": "480-510"},
            ],
        }

        queries = generate_asset_queries(scenes, platform="youtube_dark")

        self.assertNotIn("preferir_imagem", queries[0])
        self.assertTrue(queries[1].get("preferir_imagem"))
        self.assertNotIn("preferir_imagem", queries[2])

    def test_tiktok_shop_no_preferir_imagem(self):
        scenes = {
            "angulo": "problema_solucao",
            "produto": "Produto X",
            "cenas": [
                {"tipo": "contexto", "visual": "product", "tempo": "0-5"},
            ],
        }

        queries = generate_asset_queries(scenes, platform="tiktok_shop")

        self.assertNotIn("preferir_imagem", queries[0])


if __name__ == "__main__":
    unittest.main()
