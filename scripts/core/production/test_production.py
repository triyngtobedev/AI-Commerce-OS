"""
Testes da infraestrutura de produção contínua.
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

from scripts.core.production.hash_utils import hash_content, hash_file
from scripts.core.production.logger import ProductionLogger, LogLevel
from scripts.core.production.pipeline_state import PipelineState, STAGE_ORDER, PIPELINE_VERSION
from scripts.core.production.stage_cache import StageCache
from scripts.core.production.health_check import HealthCheckReport, run_health_check
from scripts.core.production.manifest import generate_production_manifest, MANIFEST_FILENAME
from scripts.core.production.performance_audit import generate_performance_report
from scripts.core.production.monetization_audit import run_monetization_audit
from scripts.core.production.retry import retry_with_backoff


class TestHashUtils(unittest.TestCase):
    def test_hash_content_deterministic(self):
        h1 = hash_content({"a": 1, "b": 2})
        h2 = hash_content({"b": 2, "a": 1})
        self.assertEqual(h1, h2)

    def test_hash_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.txt"
            path.write_text("hello", encoding="utf-8")
            self.assertIsNotNone(hash_file(path))
            self.assertIsNone(hash_file(Path(tmp) / "missing.txt"))


class TestProductionLogger(unittest.TestCase):
    def test_levels(self):
        logger = ProductionLogger("test")
        logger.info("info msg")
        logger.success("success msg")
        logger.warning("warn msg")
        entries = logger.get_entries()
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["level"], LogLevel.INFO.value)


class TestPipelineState(unittest.TestCase):
    def test_save_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            state = PipelineState(output_dir)
            state.mark_completed("collect", 1.5)
            state.mark_completed("analysis", 2.0)

            state2 = PipelineState(output_dir)
            self.assertTrue(state2.is_completed("collect"))
            self.assertEqual(state2.get_resume_stage(), "strategy")

    def test_stage_order(self):
        self.assertIn("upload", STAGE_ORDER)
        self.assertIn("manifest", STAGE_ORDER)


class TestStageCache(unittest.TestCase):
    def test_cache_miss_then_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            cache = StageCache(output_dir)
            artifact = output_dir / "out.json"
            artifact.write_text("{}", encoding="utf-8")

            self.assertFalse(cache.is_valid("script", {"x": 1}, [artifact]))
            cache.record("script", {"x": 1}, [artifact])
            self.assertTrue(cache.is_valid("script", {"x": 1}, [artifact]))

    def test_invalidate_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            cache = StageCache(output_dir)
            artifact = output_dir / "out.json"
            artifact.write_text("{}", encoding="utf-8")
            cache.record("script", {"x": 1}, [artifact])
            cache.record("media", {"y": 2}, [artifact])
            cache.invalidate_from("script", STAGE_ORDER)
            self.assertFalse(cache.is_valid("script", {"x": 1}, [artifact]))


class TestRetry(unittest.TestCase):
    def test_retry_succeeds_on_second_attempt(self):
        attempts = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0.01, operation="test")
        def flaky():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ConnectionError("fail")
            return "ok"

        self.assertEqual(flaky(), "ok")
        self.assertEqual(attempts["count"], 2)


class TestHealthCheck(unittest.TestCase):
    def test_report_structure(self):
        report = HealthCheckReport(valid=True)
        report.add("test_check", True, "ok")
        report.add("fail_check", False, "missing")
        self.assertFalse(report.valid)
        self.assertEqual(len(report.errors), 1)

    def test_run_health_check_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "post_package.json").write_text("{}", encoding="utf-8")
            result = {
                "conteudo": {
                    "titulo": "Título de Teste Válido",
                    "descricao": "Descrição longa o suficiente para passar na validação mínima.",
                    "tags": ["a", "b", "c"],
                    "idioma": "pt-BR",
                    "categoria_youtube": "Education",
                },
                "cenas": {"cenas": [{}, {}, {}]},
            }
            report = run_health_check(folder, result)
            self.assertIsNotNone(report)
            (folder / "health_check_report.json").exists()


class TestManifest(unittest.TestCase):
    def test_generate_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "analysis.json").write_text("{}", encoding="utf-8")
            result = {
                "produto": {"nome": "Teste", "categoria": "historia"},
                "conteudo": {"titulo": "T", "descricao": "D", "tags": []},
                "roteiro": {"hook": "H"},
                "cenas": {},
            }
            path = generate_production_manifest(
                folder,
                result,
                pipeline_state={"step_timings": {"script": 1.0}, "providers_used": ["stock"]},
            )
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["pipeline_version"], PIPELINE_VERSION)


class TestPerformanceAudit(unittest.TestCase):
    def test_generate_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = generate_performance_report(
                folder,
                {"step_timings": {"script": 10, "media": 30, "render": 60}, "providers_used": []},
            )
            self.assertIn("bottlenecks", report)
            self.assertGreater(report["total_seconds"], 0)


class TestMonetizationAudit(unittest.TestCase):
    def test_no_alerts_clean_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            result = {
                "conteudo": {"titulo": "Título Único Novo"},
                "roteiro": {"hook": "Hook único", "contexto": "Contexto único"},
                "youtube_metadata": {},
            }
            with patch(
                "scripts.core.production.monetization_audit._load_previous_manifests",
                return_value=[],
            ):
                report = run_monetization_audit(result, folder)
            self.assertEqual(report["risk_level"], "low")


if __name__ == "__main__":
    unittest.main()
