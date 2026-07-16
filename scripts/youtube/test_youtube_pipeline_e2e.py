"""
Testes End-to-End do pipeline YouTube Dark.

Valida o fluxo completo com mocks para APIs externas (IA, mídia, render).
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.core.platform_config import YOUTUBE_DARK
from scripts.publisher.youtube_auth import CredentialStatus


SAMPLE_TOPIC = {
    "nome": "Teste E2E Pipeline YouTube",
    "categoria": "historia",
    "subcategoria": "teste",
    "keywords": ["teste", "historia", "e2e"],
    "potencial_monetizacao": "alto",
    "dificuldade_pesquisa": "baixa",
    "angulo_sugerido": "revelacao_historica",
    "content_type": "topic",
}

MOCK_ANALYSIS = {
    "score": 90,
    "potencial": "alto",
    "publico_alvo": "Interessados em história",
    "motivos": ["Tema com alto apelo", "Produção viável"],
    "facilidade_producao": "alta",
    "potencial_watch_time": "alto",
    "disponibilidade_midia": "alta",
    "risco_conteudo": "baixo",
    "gancho": "Você não vai acreditar nessa história",
}

MOCK_STRATEGY = {
    "angulo": "revelacao_historica",
    "tom": "documentario",
    "estrutura": "narrativa_cronologica",
    "formato": YOUTUBE_DARK.formato,
}

def _long_narration_text():
    """Gera narração longa o suficiente para passar validação do pipeline."""

    base = (
        "Em uma manhã qualquer, tudo mudou. "
        "O contexto histórico era complexo e envolvia múltiplas forças. "
        "Os eventos se desenrolaram rapidamente ao longo de décadas. "
        "A verdade surpreendeu a todos os envolvidos na época. "
        "O impacto foi duradouro e ainda ressoa nos dias de hoje. "
        "E essa história permanece viva na memória coletiva. "
    )
    return base * 65


MOCK_SCRIPT = {
    "hook": "Em uma manhã qualquer, tudo mudou para sempre.",
    "contexto": "O contexto histórico era complexo e envolvia múltiplas forças políticas.",
    "desenvolvimento": _long_narration_text(),
    "revelacao": "A verdade surpreendeu a todos os envolvidos na época.",
    "consequencias": "O impacto foi duradouro e ainda ressoa nos dias de hoje.",
    "encerramento": "E essa história permanece viva. Inscreva-se para mais.",
}

MOCK_CONTENT = {
    "titulo": "A História Que Ninguém Contou — Teste E2E",
    "descricao": "Descubra os fatos surpreendentes deste evento histórico.",
    "tags": ["história", "documentário", "teste"],
    "texto_narracao": _long_narration_text(),
    "duracao": "8 minutos",
    "categoria_youtube": "Education",
    "thumbnail_texto": "Teste E2E",
}


class TestYouTubePipelineE2E(unittest.TestCase):
    """Testa fluxo completo do pipeline YouTube Dark."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.topics_file = Path(self.temp_dir) / "topics_source.json"
        self.topics_file.write_text(
            json.dumps([SAMPLE_TOPIC]),
            encoding="utf-8",
        )

    def _patch_pipeline(self):
        """Retorna dict de patches para isolar APIs externas."""

        mock_video = Path(self.temp_dir) / "video_final.mp4"
        mock_video.write_bytes(b"fake video content")

        mock_audio = Path(self.temp_dir) / "narracao.mp3"
        mock_audio.write_bytes(b"fake audio")

        mock_thumbnail = Path(self.temp_dir) / "thumbnail.jpg"
        mock_thumbnail.write_bytes(b"fake thumbnail")

        return {
            "collect": patch(
                "scripts.pipeline.youtube_pipeline.collect_topics",
                return_value=[SAMPLE_TOPIC],
            ),
            "analyze": patch(
                "scripts.pipeline.youtube_pipeline.analyze_topic",
                return_value=MOCK_ANALYSIS,
            ),
            "strategy": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_strategy",
                return_value=MOCK_STRATEGY,
            ),
            "script": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_script",
                return_value=MOCK_SCRIPT,
            ),
            "content": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_content",
                return_value=MOCK_CONTENT,
            ),
            "scenes": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_scenes",
                return_value={
                    "cenas": [
                        {
                            "tipo": "hook",
                            "narracao": "Cena 1",
                            "query": "historical event",
                            "timing": "0-30",
                        }
                    ]
                },
            ),
            "media": patch(
                "scripts.pipeline.youtube_pipeline"
                ".run_media_pipeline",
                return_value="stock",
            ),
            "audio": patch(
                "scripts.pipeline.youtube_pipeline.create_audio",
                return_value=str(mock_audio),
            ),
            "render": patch(
                "scripts.pipeline.youtube_pipeline"
                ".render_video_project",
                return_value=mock_video,
            ),
            "thumbnail": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_thumbnail",
                return_value=str(mock_thumbnail),
            ),
            "prepare": patch(
                "scripts.pipeline.youtube_pipeline.prepare_assets",
            ),
            "caption": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_caption",
                return_value={"legenda": "test"},
            ),
            "queries": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_asset_queries",
                return_value=["historical documentary"],
            ),
            "subtitles": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_subtitles",
                return_value=None,
            ),
            "build_project": patch(
                "scripts.pipeline.youtube_pipeline"
                ".build_video_project",
            ),
            "record": patch(
                "scripts.pipeline.youtube_pipeline"
                ".record_production",
            ),
            "output_dir": patch(
                "scripts.pipeline.youtube_pipeline"
                ".content_output_dir",
                return_value=Path(self.temp_dir) / "output",
            ),
            "processed": patch(
                "scripts.pipeline.youtube_pipeline"
                ".collect_processed_topic_names",
                return_value=set(),
            ),
        }

    def test_full_pipeline_produces_result(self):
        """Pipeline deve percorrer todas as etapas e retornar resultado."""

        patches = self._patch_pipeline()

        with patches["collect"], patches["analyze"], \
             patches["strategy"], patches["script"], \
             patches["content"], patches["scenes"], \
             patches["media"], patches["audio"], \
             patches["render"], patches["thumbnail"], \
             patches["prepare"], patches["caption"], \
             patches["queries"], patches["subtitles"], \
             patches["build_project"], patches["record"], \
             patches["output_dir"], patches["processed"]:

            from scripts.pipeline.youtube_pipeline import (
                run_youtube_pipeline,
            )

            results = run_youtube_pipeline(
                max_videos=1,
                auto_upload=False,
            )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(
            result["platform"],
            YOUTUBE_DARK.id,
        )
        self.assertIn("conteudo", result)
        self.assertIn("roteiro", result)
        self.assertIn("cenas", result)
        self.assertEqual(
            result["conteudo"]["texto_narracao"],
            MOCK_CONTENT["texto_narracao"],
        )

    def test_pipeline_discards_low_score_topic(self):
        """Tema com score baixo deve ser descartado."""

        low_analysis = {**MOCK_ANALYSIS, "score": 30}

        patches = self._patch_pipeline()

        with patches["collect"], \
             patch(
                 "scripts.pipeline.youtube_pipeline.analyze_topic",
                 return_value=low_analysis,
             ), \
             patches["prepare"]:

            from scripts.pipeline.youtube_pipeline import (
                run_youtube_pipeline,
            )

            results = run_youtube_pipeline(max_videos=1)

        self.assertEqual(len(results), 0)

    def test_pipeline_upload_when_configured(self):
        """Upload deve ser chamado quando publicação habilitada."""

        patches = self._patch_pipeline()

        mock_upload_result = {
            "status": "UPLOADED",
            "video_id": "abc123",
            "url": "https://youtube.com/watch?v=abc123",
        }

        with patches["collect"], patches["analyze"], \
             patches["strategy"], patches["script"], \
             patches["content"], patches["scenes"], \
             patches["media"], patches["audio"], \
             patches["render"], patches["thumbnail"], \
             patches["prepare"], patches["caption"], \
             patches["queries"], patches["subtitles"], \
             patches["build_project"], patches["record"], \
             patches["output_dir"], patches["processed"], \
             patch(
                 "scripts.pipeline.youtube_pipeline"
                 ".is_upload_configured",
                 return_value=True,
             ), \
             patch(
                 "scripts.pipeline.youtube_pipeline"
                 ".upload_from_folder",
                 return_value=mock_upload_result,
             ) as mock_upload:

            from scripts.pipeline.youtube_pipeline import (
                run_youtube_pipeline,
            )

            results = run_youtube_pipeline(
                max_videos=1,
                auto_upload=True,
            )

        self.assertEqual(len(results), 1)
        mock_upload.assert_called_once()

    def test_pipeline_skips_upload_when_disabled(self):
        """Upload não deve ser chamado sem flag nem env."""

        patches = self._patch_pipeline()

        with patches["collect"], patches["analyze"], \
             patches["strategy"], patches["script"], \
             patches["content"], patches["scenes"], \
             patches["media"], patches["audio"], \
             patches["render"], patches["thumbnail"], \
             patches["prepare"], patches["caption"], \
             patches["queries"], patches["subtitles"], \
             patches["build_project"], patches["record"], \
             patches["output_dir"], patches["processed"], \
             patch(
                 "scripts.pipeline.youtube_pipeline"
                 ".upload_from_folder",
             ) as mock_upload, \
             patch.dict("os.environ", {}, clear=True):

            from scripts.pipeline.youtube_pipeline import (
                run_youtube_pipeline,
            )

            run_youtube_pipeline(
                max_videos=1,
                auto_upload=False,
            )

        mock_upload.assert_not_called()

    def test_pipeline_no_topics_returns_empty(self):
        """Sem temas, pipeline retorna lista vazia."""

        with patch(
            "scripts.pipeline.youtube_pipeline.collect_topics",
            return_value=[],
        ):
            from scripts.pipeline.youtube_pipeline import (
                run_youtube_pipeline,
            )

            results = run_youtube_pipeline()

        self.assertEqual(results, [])

    def test_export_creates_artifacts(self):
        """Exportação deve gerar artefatos esperados."""

        result = {
            "platform": YOUTUBE_DARK.id,
            "produto": SAMPLE_TOPIC,
            "analise": MOCK_ANALYSIS,
            "oportunidade": {
                "score_venda": 90,
                "decisao": "CRIAR_VIDEO",
            },
            "acao": "CRIAR_VIDEO_AGORA",
            "estrategia": MOCK_STRATEGY,
            "roteiro": MOCK_SCRIPT,
            "conteudo": MOCK_CONTENT,
            "legenda": {},
            "cenas": {"cenas": []},
            "asset_queries": [],
            "audio": None,
            "video": None,
            "youtube_metadata": {
                "tags": MOCK_CONTENT["tags"],
                "categoria": "Education",
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.publisher.youtube_exporter"
                ".content_output_dir",
                return_value=Path(tmp) / "export",
            ):
                from scripts.publisher.youtube_exporter import (
                    export_youtube_video,
                )

                folder = export_youtube_video(result)

            self.assertTrue(
                (folder / "youtube_package.json").exists()
            )
            self.assertTrue(
                (folder / "content.json").exists()
            )
            self.assertTrue(
                (folder / "descricao.txt").exists()
            )
            self.assertTrue(
                (folder / "narracao.txt").exists()
            )
            self.assertTrue(
                (folder / "tags.txt").exists()
            )

            with open(
                folder / "youtube_package.json",
                encoding="utf-8",
            ) as file:
                package = json.load(file)

            self.assertEqual(
                package["titulo"],
                MOCK_CONTENT["titulo"],
            )
            self.assertEqual(
                package["platform"],
                "youtube",
            )


class TestYouTubeAnalytics(unittest.TestCase):

    def test_not_configured_returns_error(self):
        with patch.dict(os.environ, {}, clear=True):
            from scripts.youtube.youtube_analytics import (
                fetch_channel_insights,
            )

            result = fetch_channel_insights()

        self.assertFalse(result["configured"])
        self.assertIn("error", result)

    def test_optimization_insights_structure(self):
        from scripts.youtube.youtube_analytics import (
            OptimizationInsights,
        )

        insights = OptimizationInsights(
            best_performing_titles=["Title A"],
            average_ctr=4.5,
            average_retention=55.0,
            recommendations=["Test recommendation"],
        )

        data = insights.to_dict()

        self.assertEqual(data["average_ctr"], 4.5)
        self.assertEqual(len(data["recommendations"]), 1)


class TestPlatformConfig(unittest.TestCase):

    def test_youtube_dark_config(self):
        self.assertEqual(YOUTUBE_DARK.id, "youtube_dark")
        self.assertEqual(YOUTUBE_DARK.render.width, 1920)
        self.assertEqual(YOUTUBE_DARK.render.height, 1080)
        self.assertEqual(YOUTUBE_DARK.scene_count, 8)


if __name__ == "__main__":
    unittest.main()
