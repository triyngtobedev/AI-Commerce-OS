"""
Validação de providers e tokens externos — ai-commerce-os.

Verifica disponibilidade de ferramentas locais (ffmpeg, Real-ESRGAN) e
presença de variáveis de ambiente para APIs externas.

Uso:
  python scripts/validate_providers.py
  python scripts/validate_providers.py --strict   # exit 1 se algo crítico faltar
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

CRITICAL_VARS = [
    "PIPELINE_API_KEY",
    "GEMINI_API_KEY",
]

OPTIONAL_VARS = [
    ("GROQ_API_KEY", "Fallback LLM"),
    ("OPENROUTER_API_KEY", "Fallback LLM alternativo"),
    ("PEXELS_API_KEY", "Mídia stock Pexels"),
    ("PIXABAY_API_KEY", "Mídia stock Pixabay"),
    ("CLOUD_API_KEY", "Alias da chave Railway"),
    ("YOUTUBE_CLIENT_ID", "Upload YouTube OAuth"),
    ("YOUTUBE_CLIENT_SECRET", "Upload YouTube OAuth"),
    ("YOUTUBE_REFRESH_TOKEN", "Upload YouTube OAuth"),
    ("HF_TOKEN", "HuggingFace media provider (HF_API_TOKEN também aceito)"),
    ("AZURE_SPEECH_KEY", "TTS Azure"),
]


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}\n{'─' * 50}")


def check_video_upscaler() -> tuple[list[str], list[str]]:
    passed: list[str] = []
    warnings: list[str] = []

    section("Video upscaler")
    try:
        from src.video_upscaler import ffmpeg_available, realesrgan_available

        if ffmpeg_available():
            ok("ffmpeg disponível no PATH")
            passed.append("ffmpeg")
        else:
            fail("ffmpeg ausente — upscale e remux não funcionarão")
            warnings.append("ffmpeg ausente")

        if realesrgan_available():
            ok("realesrgan-ncnn-vulkan disponível (upscale GPU/CPU)")
            passed.append("realesrgan")
        else:
            warn("realesrgan-ncnn-vulkan ausente — fallback para upscale bicubic via ffmpeg")
            warnings.append("realesrgan opcional ausente")
    except ImportError as exc:
        fail(f"Não foi possível importar src.video_upscaler: {exc}")
        warnings.append("video_upscaler import failed")

    return passed, warnings


def check_env_vars() -> tuple[list[str], list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []

    section("Tokens e variáveis de ambiente")

    for var in CRITICAL_VARS:
        if os.getenv(var):
            ok(f"{var} configurada")
            passed.append(var)
        else:
            fail(f"{var} ausente (crítica)")
            failed.append(var)

    for var, desc in OPTIONAL_VARS:
        if var == "HF_TOKEN":
            if os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN"):
                ok(f"HF_TOKEN/HF_API_TOKEN configurado — {desc}")
                passed.append("HF_TOKEN|HF_API_TOKEN")
            else:
                warn(f"HF_TOKEN/HF_API_TOKEN ausente — {desc}")
            continue
        if os.getenv(var):
            ok(f"{var} configurada — {desc}")
            passed.append(var)
        else:
            warn(f"{var} ausente — {desc}")

    youtube_file = ROOT / ".env.youtube"
    if youtube_file.exists():
        ok(".env.youtube encontrado")
        passed.append(".env.youtube")
    else:
        warn(".env.youtube ausente — execute: python scripts/youtube/gerar_token.py")

    return passed, failed, warnings


def check_database_path() -> tuple[list[str], list[str]]:
    passed: list[str] = []
    warnings: list[str] = []

    section("Persistência")

    db_path = Path(os.getenv("DATABASE_PATH", str(ROOT / "database" / "pipeline_jobs.db")))
    if db_path.parent.exists():
        ok(f"Diretório do banco existe: {db_path.parent}")
        passed.append("db_dir")
    else:
        warn(f"Diretório do banco será criado em runtime: {db_path.parent}")

    persistent = Path("/app/persistent")
    if persistent.is_dir():
        ok("Volume persistente montado em /app/persistent")
        passed.append("persistent_volume")
    else:
        warn("Sem volume /app/persistent — normal em dev local")

    return passed, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida providers e tokens do ai-commerce-os")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Retorna exit code 1 se variáveis críticas ou ffmpeg faltarem",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}Validação de providers — ai-commerce-os{RESET}")

    _, upscaler_warnings = check_video_upscaler()
    _, critical_failed, _ = check_env_vars()
    _, _ = check_database_path()

    section("Resumo")
    if critical_failed:
        fail(f"Variáveis críticas ausentes: {', '.join(critical_failed)}")
    else:
        ok("Variáveis críticas OK")

    if "ffmpeg ausente" in upscaler_warnings:
        fail("ffmpeg é obrigatório para o pipeline de vídeo")

    if args.strict and (critical_failed or "ffmpeg ausente" in upscaler_warnings):
        print(f"\n{RED}{BOLD}Validação strict falhou.{RESET}\n")
        return 1

    print(f"\n{GREEN}{BOLD}Validação concluída.{RESET}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
