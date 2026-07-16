"""
Testes do modo RERUN (--rerun / --force) para reprocessamento em desenvolvimento.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.core.platform_config import YOUTUBE_DARK
from scripts.core.production.pipeline_state import PipelineState
from scripts.core.production.resumable_pipeline import run_resumable_youtube_pipeline
from scripts.core.production.stage_cache import StageCache
from scripts.utils.slug import content_output_dir
from scripts.youtube.topic_selector import select_next_topics

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


class TestRerunTopicSelection(unittest.TestCase):

    def test_force_selects_when_all_topics_processed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.youtube.topic_selector.get_processed_subject_names",
                return_value=[
                    TOPIC_A["nome"],
                    TOPIC_B["nome"],
                    TOPIC_C["nome"],
                ],
            ):
                without_force = select_next_topics(
                    [TOPIC_A, TOPIC_B, TOPIC_C],
                    max_videos=1,
                    output_base=tmp,
                    force=False,
                )
                with_force = select_next_topics(
                    [TOPIC_A, TOPIC_B, TOPIC_C],
                    max_videos=1,
                    output_base=tmp,
                    force=True,
                )

        self.assertEqual(without_force, [])
        self.assertEqual(len(with_force), 1)

    def test_rerun_reuses_existing_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = content_output_dir(
                TOPIC_A,
                base=tmp,
                platform=YOUTUBE_DARK.id,
            ).resolve()
            output_dir.mkdir(parents=True)
            marker = output_dir / "content.json"
            marker.write_text("{}", encoding="utf-8")

            with patch(
                "scripts.youtube.topic_selector.get_processed_subject_names",
                return_value=[TOPIC_A["nome"]],
            ):
                selected = select_next_topics(
                    [TOPIC_A, TOPIC_B],
                    max_videos=1,
                    output_base=tmp,
                    force=True,
                )

            rerun_dir = content_output_dir(
                selected[0],
                base=tmp,
                platform=YOUTUBE_DARK.id,
            ).resolve()

            self.assertEqual(selected[0]["nome"], TOPIC_A["nome"])
            self.assertEqual(rerun_dir, output_dir)
            self.assertTrue(marker.exists())


class TestRerunStageCache(unittest.TestCase):

    def test_force_invalidates_stage_cache_and_completed_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "rerun-topic"
            output_dir.mkdir(parents=True)

            artifact = output_dir / "analysis.json"
            artifact.write_text("{}", encoding="utf-8")

            cache = StageCache(output_dir)
            cache.record("analysis", {"nome": "T"}, [artifact])
            cache.record("strategy", {"topic": "T"}, [artifact])

            state = PipelineState(output_dir)
            state.mark_completed("collect", 1.0)
            state.mark_completed("analysis", 2.0)

            topic = {"nome": "Rerun Topic", "categoria": "historia"}
            cache_cleared = {"value": False}

            def fake_timed(ctx, stage, fn):
                if stage == "collect" and not cache_cleared["value"]:
                    reloaded = StageCache(ctx.output_dir)
                    cache_cleared["value"] = not reloaded._data.get("stages")
                    if PipelineState(ctx.output_dir).completed_steps:
                        raise AssertionError(
                            "completed_steps deveria estar vazio com force=True"
                        )
                if stage == "collect":
                    return topic
                raise RuntimeError("stop-after-force-check")

            with patch(
                "scripts.core.production.resumable_pipeline.content_output_dir",
                return_value=output_dir,
            ), patch(
                "scripts.core.production.resumable_pipeline._timed_stage",
                side_effect=fake_timed,
            ), patch(
                "scripts.core.production.resumable_pipeline.prepare_assets",
            ):
                result = run_resumable_youtube_pipeline(topic, force=True)

            self.assertIsNone(result)
            self.assertTrue(cache_cleared["value"])
            self.assertEqual(
                StageCache(output_dir)._data.get("stages", {}),
                {},
            )
            self.assertEqual(PipelineState(output_dir).completed_steps, [])

    def test_without_force_preserves_stage_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "cached-topic"
            output_dir.mkdir(parents=True)

            artifact = output_dir / "analysis.json"
            artifact.write_text("{}", encoding="utf-8")

            cache = StageCache(output_dir)
            cache.record("analysis", {"nome": "T"}, [artifact])

            topic = {"nome": "Cached Topic", "categoria": "historia"}

            with patch(
                "scripts.core.production.resumable_pipeline.content_output_dir",
                return_value=output_dir,
            ), patch(
                "scripts.core.production.resumable_pipeline._timed_stage",
                side_effect=RuntimeError("stop-early"),
            ), patch(
                "scripts.core.production.resumable_pipeline.prepare_assets",
            ):
                run_resumable_youtube_pipeline(topic, force=False)

            self.assertIn(
                "analysis",
                StageCache(output_dir)._data.get("stages", {}),
            )


class TestRerunCLI(unittest.TestCase):

    def test_force_flags_propagate_to_pipeline(self):
        import main

        cases = (
            (["main.py", "--platform", "youtube_dark", "--rerun"], True),
            (["main.py", "--platform", "youtube_dark", "--force"], True),
            (["main.py", "--platform", "youtube_dark"], False),
        )

        for argv, expected in cases:
            with self.subTest(argv=argv):
                with patch("main.run_youtube_pipeline") as mock_pipeline:
                    with patch.object(sys, "argv", argv):
                        main.run()

                mock_pipeline.assert_called_once()
                self.assertEqual(
                    mock_pipeline.call_args.kwargs["force"],
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
