"""
Testes das APIs de geração de vídeo.

Testes unitários (mock) rodam sem credenciais.
Testes de integração reais exigem variáveis de ambiente e são marcados com @pytest.mark.integration.

Uso:
    pytest tests/test_video_apis.py -v                    # unitários
    pytest tests/test_video_apis.py -v -m integration     # APIs reais
    python -m tests.test_video_apis                       # script standalone
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.prompt_builder import build_from_description  # noqa: E402
from src.video_generator import (  # noqa: E402
    VideoGenerator,
    falai_is_configured,
    kling_web_is_configured,
    replicate_is_configured,
)

OUTPUT_DIR = _PROJECT_ROOT / "output"
ANALYSIS_DIR = _PROJECT_ROOT / "analysis"
DEFAULT_PROMPT = "wireless earbuds on white surface, product showcase"
DEFAULT_PRODUCT = "Earbuds Pro"


# ---------------------------------------------------------------------------
# Unitários — prompt engineering
# ---------------------------------------------------------------------------


class TestPromptEngineering:
    """Valida template de prompt e-commerce."""

    def test_build_ecommerce_prompt_structure(self) -> None:
        bundle = build_from_description(
            DEFAULT_PROMPT,
            "falai",
            product_name=DEFAULT_PRODUCT,
        )
        positive = bundle["prompt"]
        assert "[PRODUCT FOCUS]" in positive
        assert DEFAULT_PRODUCT in positive
        assert "[LIGHTING]" in positive
        assert "[MOVEMENT]" in positive
        assert "[QUALITY]" in positive
        assert "4K" not in positive
        assert "watermark" in positive

    def test_build_ecommerce_prompt_without_product_name(self) -> None:
        positive = build_from_description("smart watch product video", "falai")["prompt"]
        assert "[PRODUCT FOCUS]" in positive
        assert "smart watch product video" in positive


# ---------------------------------------------------------------------------
# Unitários — fallback e retry
# ---------------------------------------------------------------------------


class TestVideoGeneratorFallback:
    """Testa cadeia de fallback sem rede."""

    def test_fallback_falai_to_replicate(self) -> None:
        generator = VideoGenerator(output_dir=OUTPUT_DIR)

        replicate_result = {
            "video_url": "https://example.com/replicate.mp4",
            "api_used": "replicate",
            "credits_remaining": None,
            "duration_seconds": 45.0,
            "resolution": "480p",
            "fallback_reason": "falai falhou (sem credenciais) → tentando replicate",
        }

        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("sem credenciais")),
            patch.object(
                generator,
                "_generate_replicate",
                return_value=MagicMock(
                    video_url=replicate_result["video_url"],
                    api_used=replicate_result["api_used"],
                    credits_remaining=None,
                    duration_seconds=45.0,
                    resolution="480p",
                    fallback_reason=None,
                    local_path=None,
                ),
            ),
            patch.object(generator, "_download_video", return_value=None),
        ):
            result = generator.generate(DEFAULT_PROMPT, product_name=DEFAULT_PRODUCT, download=False)

        assert result["api_used"] == "replicate"
        assert result["fallback_reason"] is not None
        assert "falai" in result["fallback_reason"]

    def test_all_apis_fail_raises(self) -> None:
        generator = VideoGenerator()
        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("fal down")),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("rep down")),
            patch.object(generator, "_generate_kling_web_sync", side_effect=RuntimeError("kling down")),
        ):
            with pytest.raises(RuntimeError, match="Todas as APIs"):
                generator.generate(DEFAULT_PROMPT, download=False)

    def test_retry_backoff_on_rate_limit(self) -> None:
        generator = VideoGenerator()
        call_count = 0

        def flaky(*_args: object, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("429 rate limit")
            return MagicMock(
                video_url="https://example.com/ok.mp4",
                api_used="falai",
                credits_remaining=10,
                duration_seconds=5.0,
                resolution="480p",
                fallback_reason=None,
                local_path=None,
            )

        with (
            patch.object(generator, "_generate_falai", side_effect=flaky),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("skip rep")),
            patch.object(generator, "_generate_kling_web_sync", side_effect=RuntimeError("skip kling")),
            patch.object(generator, "_download_video", return_value=None),
            patch("src.video_generator.time.sleep"),
        ):
            result = generator.generate(DEFAULT_PROMPT, download=False)

        assert result["api_used"] == "falai"
        assert call_count == 2


# ---------------------------------------------------------------------------
# Unitários — config helpers
# ---------------------------------------------------------------------------


class TestConfigHelpers:
    """Testa helpers de configuração."""

    def test_falai_requires_token(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert falai_is_configured() is False

    @pytest.mark.skipif(not falai_is_configured(), reason="HF_API_TOKEN não configurado")
    def test_falai_configured(self) -> None:
        assert falai_is_configured() is True


# ---------------------------------------------------------------------------
# Integração — APIs individuais
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFalaiIntegration:
    """Testa fal.ai via HF Router (requer HF_API_TOKEN)."""

    def test_falai_generate(self) -> None:
        if not falai_is_configured():
            pytest.skip("HF_API_TOKEN não configurado")

        generator = VideoGenerator(output_dir=OUTPUT_DIR)
        started = time.perf_counter()

        with patch.object(generator, "_download_video") as mock_dl:
            mock_dl.return_value = OUTPUT_DIR / "test_falai.mp4"
            result = generator.generate(
                DEFAULT_PROMPT,
                product_name=DEFAULT_PRODUCT,
                download=True,
            )

        elapsed = time.perf_counter() - started
        assert result["api_used"] == "falai"
        assert result["video_url"]
        assert result["duration_seconds"] > 0
        _log_api_result("falai", result, elapsed)


@pytest.mark.integration
class TestReplicateIntegration:
    """Testa Replicate (requer REPLICATE_API_TOKEN)."""

    def test_replicate_generate(self) -> None:
        if not replicate_is_configured():
            pytest.skip("REPLICATE_API_TOKEN não configurado")

        generator = VideoGenerator(output_dir=OUTPUT_DIR)

        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("skip falai")),
            patch.object(generator, "_download_video") as mock_dl,
        ):
            mock_dl.return_value = OUTPUT_DIR / "test_replicate.mp4"
            started = time.perf_counter()
            result = generator.generate(
                DEFAULT_PROMPT,
                product_name=DEFAULT_PRODUCT,
                download=True,
            )
            elapsed = time.perf_counter() - started

        assert result["api_used"] == "replicate"
        assert result["video_url"]
        _log_api_result("replicate", result, elapsed)


@pytest.mark.integration
class TestKlingWebIntegration:
    """Testa Kling Web Playwright (requer KLING_EMAIL/PASSWORD)."""

    def test_kling_web_generate(self) -> None:
        if not kling_web_is_configured():
            pytest.skip("KLING_EMAIL/KLING_PASSWORD não configurados")

        generator = VideoGenerator(output_dir=OUTPUT_DIR)

        with (
            patch.object(generator, "_generate_falai", side_effect=RuntimeError("skip falai")),
            patch.object(generator, "_generate_replicate", side_effect=RuntimeError("skip rep")),
        ):
            started = time.perf_counter()
            result = generator.generate(
                DEFAULT_PROMPT,
                product_name=DEFAULT_PRODUCT,
                download=False,
            )
            elapsed = time.perf_counter() - started

        assert result["api_used"] == "kling_web"
        _log_api_result("kling_web", result, elapsed)


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

_test_results: list[dict] = []


def _log_api_result(api_name: str, result: dict, elapsed: float) -> None:
    """Acumula resultados para relatório final."""
    _test_results.append(
        {
            "api": api_name,
            "elapsed_seconds": round(elapsed, 2),
            "api_used": result.get("api_used"),
            "credits_remaining": result.get("credits_remaining"),
            "video_url": result.get("video_url", "")[:120],
            "fallback_reason": result.get("fallback_reason"),
        }
    )

    output_file = OUTPUT_DIR / f"test_{api_name}.mp4"
    local_path = result.get("local_path")
    if local_path and Path(local_path).exists():
        Path(local_path).replace(output_file)
    elif result.get("video_url", "").startswith("file:"):
        src = Path(result["video_url"].replace("file:///", "").replace("file://", ""))
        if src.exists():
            src.replace(output_file)


def write_test_report() -> Path:
    """Gera analysis/test_results.md com resultados acumulados."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = ANALYSIS_DIR / "test_results.md"

    lines = [
        "# Resultados dos Testes de APIs de Vídeo",
        "",
        f"> Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Configuração detectada",
        "",
        f"| API | Configurada |",
        f"|-----|-------------|",
        f"| fal.ai (HF) | {'✅' if falai_is_configured() else '❌'} |",
        f"| Replicate | {'✅' if replicate_is_configured() else '❌'} |",
        f"| Kling Web | {'✅' if kling_web_is_configured() else '❌'} |",
        "",
    ]

    if _test_results:
        lines.extend(
            [
                "## Resultados por API",
                "",
                "| API | Tempo (s) | API usada | Créditos restantes | Fallback |",
                "|-----|-----------|-----------|---------------------|----------|",
            ]
        )
        for row in _test_results:
            lines.append(
                f"| {row['api']} | {row['elapsed_seconds']} | {row['api_used']} "
                f"| {row['credits_remaining']} | {row['fallback_reason'] or '—'} |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "## Resultados por API",
                "",
                "_Nenhum teste de integração executado. Rode com credenciais:_",
                "",
                "```bash",
                "pytest tests/test_video_apis.py -v -m integration",
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Comparação (preencher após testes reais)",
            "",
            "| Critério | fal.ai | Replicate | Kling Web |",
            "|----------|--------|-----------|-----------|",
            "| Velocidade | — | — | — |",
            "| Qualidade visual | — | — | — |",
            "| Créditos consumidos | — | — | — |",
            "| Estabilidade | — | — | — |",
            "",
            "## Vídeos gerados",
            "",
        ]
    )

    for api in ("falai", "replicate", "kling_web"):
        video = OUTPUT_DIR / f"test_{api}.mp4"
        status = f"✅ `{video}`" if video.exists() else "❌ não gerado"
        lines.append(f"- **{api}**: {status}")

    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Entry point standalone
# ---------------------------------------------------------------------------


def main() -> int:
    """Executa testes de integração disponíveis e gera relatório."""
    from dotenv import load_dotenv

    load_dotenv(_PROJECT_ROOT / ".env")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Testes de APIs de Vídeo ===\n")
    print(f"fal.ai configurado:     {falai_is_configured()}")
    print(f"Replicate configurado:  {replicate_is_configured()}")
    print(f"Kling Web configurado:  {kling_web_is_configured()}\n")

    tests_run = 0

    if falai_is_configured():
        print("--- Testando fal.ai ---")
        try:
            TestFalaiIntegration().test_falai_generate()
            print("fal.ai: OK\n")
            tests_run += 1
        except Exception as error:
            print(f"fal.ai: FALHOU — {error}\n")

    if replicate_is_configured():
        print("--- Testando Replicate ---")
        try:
            TestReplicateIntegration().test_replicate_generate()
            print("Replicate: OK\n")
            tests_run += 1
        except Exception as error:
            print(f"Replicate: FALHOU — {error}\n")

    if kling_web_is_configured():
        print("--- Testando Kling Web ---")
        try:
            TestKlingWebIntegration().test_kling_web_generate()
            print("Kling Web: OK\n")
            tests_run += 1
        except Exception as error:
            print(f"Kling Web: FALHOU — {error}\n")

    report = write_test_report()
    print(f"Relatório salvo em: {report}")
    print(f"Testes de integração executados: {tests_run}")

    return 0 if tests_run > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
