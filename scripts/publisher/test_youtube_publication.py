"""Testes de integração do pipeline de publicação YouTube — mocks apenas."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from scripts.publisher.youtube_exporter import export_youtube_video
from scripts.publisher.youtube_uploader import (
    UPLOAD_STATUS,
    _resolve_category_id,
    _resolve_publish_title,
    upload_video,
)


SAMPLE_RESULT = {
    "platform": "youtube_dark",
    "produto": {"nome": "Evento Tunguska"},
    "conteudo": {
        "titulo": "O Mistério de Tunguska",
        "titulo_alternativos": ["Tunguska: O Que Aconteceu?"],
        "descricao": "Descrição do vídeo.",
        "texto_narracao": "Narração completa.",
        "tags": ["história", "mistério", "tunguska"],
        "categoria_youtube": "Education",
        "idioma": "pt-BR",
    },
    "cenas": {"cenas": [{"tipo": "hook", "visual": "explosion"}]},
    "roteiro": {"hook": "Teste."},
    "estrategia": {},
    "analise": {},
    "oportunidade": {},
    "acao": "PRODUZIR",
    "legenda": {},
    "asset_queries": [],
    "youtube_metadata": {
        "capitulos": [{"tempo": "0:00", "titulo": "Intro"}],
        "tags": ["história"],
        "categoria": "Education",
        "thumbnail": None,
    },
}


class TestYouTubePublicationExport(unittest.TestCase):

    @patch("scripts.publisher.youtube_exporter.build_chapters")
    def test_export_creates_post_package(self, mock_chapters):
        mock_chapters.return_value = [{"tempo": "0:00", "titulo": "Intro"}]

        with TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake-video")

            result = dict(SAMPLE_RESULT)
            result["video"] = str(video)

            with patch(
                "scripts.publisher.youtube_exporter.content_output_dir",
                return_value=Path(tmp) / "output",
            ):
                folder = export_youtube_video(result)

            package_file = folder / "post_package.json"
            self.assertTrue(package_file.exists())

            package = json.loads(package_file.read_text(encoding="utf-8"))
            self.assertEqual(package["titulo"], "O Mistério de Tunguska")
            self.assertEqual(package["idioma"], "pt-BR")
            self.assertEqual(package["status"], "READY_TO_UPLOAD")
            self.assertIn("tags", package)
            self.assertIn("capitulos", package)


class TestYouTubePublicationUpload(unittest.TestCase):

    def test_resolve_category_id(self):
        self.assertEqual(_resolve_category_id("Education"), "27")
        self.assertEqual(_resolve_category_id("Unknown"), "27")

    @patch("scripts.publisher.youtube_uploader._load_metrics")
    def test_resolve_publish_title_avoids_duplicates(self, mock_metrics):
        mock_metrics.return_value = [
            {"status": "published", "titulo": "O Mistério de Tunguska"},
        ]
        package = {"titulo": "O Mistério de Tunguska"}
        title = _resolve_publish_title(package)
        self.assertNotEqual(title.lower(), "o mistério de tunguska")

    @patch("scripts.publisher.youtube_uploader.validate_credentials")
    def test_upload_fails_without_video(self, mock_validate):
        mock_validate.return_value = MagicMock(
            configured=True,
            valid=True,
            messages=[],
            channel_title="Test Channel",
            channel_id="UC123",
        )
        result = upload_video({"titulo": "Test", "video": "/nonexistent.mp4"})
        self.assertEqual(result["status"], UPLOAD_STATUS["failed"])


if __name__ == "__main__":
    unittest.main()
