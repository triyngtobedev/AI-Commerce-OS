import importlib
import unittest


pipeline_runner = importlib.import_module("api.services.pipeline_runner")


class TestStdoutForJob(unittest.TestCase):
    def test_stdout_tail_returns_last_n_lines(self):
        stdout = "\n".join(f"line-{i}" for i in range(150))
        tail = pipeline_runner._stdout_tail(stdout, lines=100)
        lines = tail.splitlines()
        self.assertEqual(len(lines), 100)
        self.assertEqual(lines[0], "line-50")
        self.assertEqual(lines[-1], "line-149")

    def test_stdout_for_job_includes_ai_router_when_cut_from_tail(self):
        filler = "\n".join(f"filler-{i}" for i in range(120))
        router = (
            "[AI Router] Tentando: gemini\n"
            "[AI Router] Tentando: groq/llama-3.1-8b-instant\n"
            "[Groq/llama-3.1-8b-instant] response body: ok\n"
            "[AI Router] Tentando: openrouter\n"
            "❌ Falha total: Nenhuma API de IA disponível."
        )
        stdout = f"{router}\n{filler}"
        excerpt = pipeline_runner._stdout_for_job(stdout)
        self.assertIn("--- AI Router (garantido) ---", excerpt)
        self.assertIn("[AI Router] Tentando: openrouter", excerpt)
        self.assertIn("❌ Falha total", excerpt)

    def test_failure_diagnostic_uses_extended_stdout(self):
        stdout = "\n".join(f"log-{i}" for i in range(80))
        stdout += "\n[AI Router] Tentando: openrouter\n❌ Falha total: timeout"
        diagnostic = pipeline_runner._failure_diagnostic(stdout, "")
        self.assertIn("--- stdout (últimas linhas) ---", diagnostic)
        self.assertIn("[AI Router] Tentando: openrouter", diagnostic)
        self.assertGreaterEqual(len(diagnostic.splitlines()), 80)

    def test_extract_failure_reason_from_stdout(self):
        stdout = (
            "Pipeline ok\n"
            "❌ Erro processando Tunguska: Nenhuma API de IA disponível.\n"
        )
        reason = pipeline_runner._extract_failure_reason(stdout, "")
        self.assertIn("Erro processando", reason)

    def test_extract_failure_reason_prefers_stdout_over_stderr(self):
        stdout = "❌ Pipeline concluiu sem produzir vídeo final."
        stderr = "some stderr noise"
        reason = pipeline_runner._extract_failure_reason(stdout, stderr)
        self.assertIn("Pipeline concluiu", reason)


if __name__ == "__main__":
    unittest.main()
