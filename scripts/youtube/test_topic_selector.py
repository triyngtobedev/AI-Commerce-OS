"""
Testes de seleção de temas YouTube Dark.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.core.platform_config import YOUTUBE_DARK
from scripts.utils.slug import content_output_dir
from scripts.youtube.topic_selector import (
    collect_processed_topic_names,
    is_topic_processed,
    resolve_topic_for_production,
    select_next_topics,
)

TOPIC_A = {
    "nome": "O Mistério da Explosão de Tunguska",
    "categoria": "historia",
    "potencial_monetizacao": "alto",
    "dificuldade_pesquisa": "baixa",
}

TOPIC_B = {
    "nome": "A Verdade Sobre a Biblioteca de Alexandria",
    "categoria": "historia",
    "potencial_monetizacao": "alto",
    "dificuldade_pesquisa": "baixa",
}

TOPIC_C = {
    "nome": "Como a Peste Negra Mudou a Europa Para Sempre",
    "categoria": "historia",
    "potencial_monetizacao": "medio",
    "dificuldade_pesquisa": "media",
}


class TestTopicSelector(unittest.TestCase):

    def test_selects_highest_unprocessed_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.youtube.topic_selector.get_processed_subject_names",
                return_value=[TOPIC_A["nome"]],
            ):
                selected = select_next_topics(
                    [TOPIC_A, TOPIC_B, TOPIC_C],
                    max_videos=1,
                    output_base=tmp,
                )

        self.assertEqual(len(selected), 1)
        self.assertEqual(
            selected[0]["nome"],
            TOPIC_B["nome"],
        )

    def test_skips_all_when_every_topic_processed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.youtube.topic_selector.get_processed_subject_names",
                return_value=[
                    TOPIC_A["nome"],
                    TOPIC_B["nome"],
                    TOPIC_C["nome"],
                ],
            ):
                selected = select_next_topics(
                    [TOPIC_A, TOPIC_B, TOPIC_C],
                    max_videos=1,
                    output_base=tmp,
                )

        self.assertEqual(selected, [])

    def test_detects_processed_topic_from_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = content_output_dir(
                TOPIC_A,
                base=tmp,
                platform=YOUTUBE_DARK.id,
            )
            output_dir.mkdir(parents=True)
            (output_dir / "content.json").write_text(
                "{}",
                encoding="utf-8",
            )

            processed = collect_processed_topic_names(
                platform=YOUTUBE_DARK.id,
                output_base=tmp,
            )

            self.assertIn(
                output_dir.name,
                processed,
            )
            self.assertTrue(
                is_topic_processed(
                    TOPIC_A,
                    processed_names=processed,
                    platform=YOUTUBE_DARK.id,
                    output_base=tmp,
                )
            )

    def test_resolve_replaces_processed_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.youtube.topic_selector.get_processed_subject_names",
                return_value=[TOPIC_A["nome"]],
            ):
                resolved = resolve_topic_for_production(
                    TOPIC_A,
                    [TOPIC_A, TOPIC_B, TOPIC_C],
                    output_base=tmp,
                )

        self.assertEqual(
            resolved["nome"],
            TOPIC_B["nome"],
        )

    def test_force_topic_ignores_history(self):
        with patch(
            "scripts.youtube.topic_selector.get_processed_subject_names",
            return_value=[TOPIC_A["nome"]],
        ):
            selected = select_next_topics(
                [TOPIC_A, TOPIC_B],
                max_videos=1,
                force_topic_name=TOPIC_A["nome"],
            )

        self.assertEqual(
            selected[0]["nome"],
            TOPIC_A["nome"],
        )

    def test_selects_multiple_distinct_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.youtube.topic_selector.get_processed_subject_names",
                return_value=[],
            ):
                selected = select_next_topics(
                    [TOPIC_A, TOPIC_B, TOPIC_C],
                    max_videos=2,
                    output_base=tmp,
                )

        self.assertEqual(len(selected), 2)
        names = {topic["nome"] for topic in selected}
        self.assertEqual(len(names), 2)


class TestYouTubePipelineTopicSelection(unittest.TestCase):

    def test_pipeline_uses_next_unprocessed_topic(self):
        from scripts.pipeline.youtube_pipeline import run_youtube_pipeline

        processed = {
            TOPIC_A["nome"].strip().casefold(),
            content_output_dir(
                TOPIC_A,
                platform=YOUTUBE_DARK.id,
            ).name,
        }

        patches = {
            "collect": patch(
                "scripts.pipeline.youtube_pipeline.collect_topics",
                return_value=[TOPIC_A, TOPIC_B],
            ),
            "processed": patch(
                "scripts.pipeline.youtube_pipeline"
                ".collect_processed_topic_names",
                return_value=processed,
            ),
            "analyze": patch(
                "scripts.pipeline.youtube_pipeline.analyze_topic",
                return_value={"score": 90},
            ),
            "opportunity": patch(
                "scripts.pipeline.youtube_pipeline"
                ".analyze_topic_opportunity",
                return_value={"score_venda": 90},
            ),
            "decide": patch(
                "scripts.pipeline.youtube_pipeline.decide_action",
                return_value="CRIAR_VIDEO_AGORA",
            ),
            "strategy": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_strategy",
                return_value={"angulo": "revelacao_historica"},
            ),
            "script": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_script",
                return_value={"hook": "x"},
            ),
            "content": patch(
                "scripts.pipeline.youtube_pipeline"
                ".generate_youtube_content",
                return_value={
                    "texto_narracao": "palavra " * 420,
                    "titulo": "Alexandria Test",
                    "tags": ["historia"],
                },
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
                "scripts.pipeline.youtube_pipeline.run_media_pipeline",
            ),
            "audio": patch(
                "scripts.pipeline.youtube_pipeline.create_audio",
                return_value="audio.mp3",
            ),
            "caption": patch(
                "scripts.pipeline.youtube_pipeline.generate_caption",
                return_value={},
            ),
            "queries": patch(
                "scripts.pipeline.youtube_pipeline.generate_asset_queries",
                return_value=[],
            ),
            "subtitles": patch(
                "scripts.pipeline.youtube_pipeline.generate_subtitles",
                return_value=None,
            ),
            "build": patch(
                "scripts.pipeline.youtube_pipeline.build_video_project",
            ),
            "render": patch(
                "scripts.pipeline.youtube_pipeline.render_video_project",
                return_value=None,
            ),
            "thumbnail": patch(
                "scripts.pipeline.youtube_pipeline.generate_thumbnail",
                return_value=None,
            ),
            "export": patch(
                "scripts.pipeline.youtube_pipeline.export_youtube_video",
                return_value=Path("output/fake"),
            ),
            "record": patch(
                "scripts.pipeline.youtube_pipeline.record_production",
            ),
            "prepare": patch(
                "scripts.pipeline.youtube_pipeline.prepare_assets",
            ),
            "output_dir": patch(
                "scripts.pipeline.youtube_pipeline.content_output_dir",
                return_value=Path("output/fake"),
            ),
        }

        with patches["collect"], patches["processed"], \
             patches["analyze"], patches["opportunity"], \
             patches["decide"], patches["strategy"], \
             patches["script"], patches["content"], \
             patches["scenes"], patches["media"], \
             patches["audio"], patches["caption"], \
             patches["queries"], patches["subtitles"], \
             patches["build"], patches["render"], \
             patches["thumbnail"], patches["export"], \
             patches["record"], patches["prepare"], \
             patches["output_dir"]:

            results = run_youtube_pipeline(max_videos=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["produto"]["nome"],
            TOPIC_B["nome"],
        )


    def test_real_environment_skips_tunguska_and_alexandria(self):
        """Com histórico real, deve sobrar apenas Peste Negra."""

        selected = select_next_topics(
            [TOPIC_A, TOPIC_B, TOPIC_C],
            max_videos=1,
        )

        if selected:
            self.assertEqual(
                selected[0]["nome"],
                TOPIC_C["nome"],
            )


if __name__ == "__main__":
    unittest.main()
