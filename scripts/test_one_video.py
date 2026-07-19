#!/usr/bin/env python3
"""
Roda o pipeline YouTube Dark completo para UM vídeo de teste.

Providers gratuitos apenas:
  LLM     → Gemini + Groq
  Footage → Wikimedia + Pixabay (sem Pexels)
  TTS     → Edge TTS (fallback gratuito)

Uso:
  python3 scripts/test_one_video.py
  python3 scripts/test_one_video.py --topic "Outro Tema"
  python3 scripts/test_one_video.py --force
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import traceback
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def _load_env() -> None:
    """Load .env when present; Railway/production vars already live in os.environ."""
    from dotenv import load_dotenv

    env_file = ROOT / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_TOPIC = "Os Mistérios das Pirâmides de Gizé"

STAGE_ORDER = (
    "topic analysis",
    "script",
    "scenes",
    "audio",
    "footage",
    "render",
)


def _banner(title: str) -> None:
    line = "═" * 56
    print(f"\n{line}\n {title}\n{line}")


def _stage_label(name: str) -> None:
    print(f"\n▶ STAGE: {name}")


def _check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg não encontrado no PATH. "
            "Instale com: sudo apt-get update && sudo apt-get install -y ffmpeg"
        )
    print("✓ FFmpeg disponível:", shutil.which("ffmpeg"))


def _configure_free_providers() -> None:
    """Garante modo free-only: sem Pexels/Azure; Edge TTS como fallback."""
    os.environ.pop("PEXELS_API_KEY", None)
    os.environ.pop("AZURE_SPEECH_KEY", None)
    os.environ.pop("AZURE_SPEECH_REGION", None)
    os.environ.setdefault("DEFAULT_PLATFORM", "youtube_dark")
    os.environ.setdefault("YOUTUBE_AUTO_UPLOAD", "false")
    os.environ.setdefault("SPRINT30_ENABLED", "true")
    os.environ.setdefault("SPRINT30_VISUAL_SCORE", "true")
    os.environ.setdefault("SPRINT30_THUMBNAIL_AB", "false")
    os.environ.setdefault("SPRINT30_AUDIO_LAYER", "true")
    os.environ.setdefault("SPRINT30_RETENTION_CONTROLLER", "true")
    os.environ.setdefault("SPRINT30_METRICS", "true")


def _preflight_keys() -> None:
    from scripts.ai.router import get_client

    health = get_client().health()
    if not health.get("ai_any"):
        raise RuntimeError(
            "Nenhuma chave de IA configurada. "
            "Defina GEMINI_API_KEY e/ou GROQ_API_KEY (env vars ou .env local)."
        )

    footage = health.get("footage", {})
    if not footage.get("pixabay"):
        print(
            "⚠ PIXABAY_API_KEY ausente — footage usará principalmente Wikimedia "
            "(pode reduzir variedade de clipes)."
        )

    tts = health.get("tts", {})
    if not tts.get("azure"):
        print("ℹ TTS: Edge TTS gratuito (Azure não configurado).")


@contextmanager
def _stage_tracker():
    state = {"current": "startup"}

    def wrap(stage: str, fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            state["current"] = stage
            _stage_label(stage)
            return fn(*args, **kwargs)

        return inner

    import scripts.pipeline.youtube_pipeline as pipeline

    patches = [
        (pipeline, "analyze_topic", "topic analysis"),
        (pipeline, "generate_youtube_script", "script"),
        (pipeline, "generate_youtube_scenes", "scenes"),
        (pipeline, "create_audio", "audio"),
        (pipeline, "run_media_pipeline", "footage"),
        (pipeline, "render_video_project", "render"),
    ]

    originals = {}
    for module, attr, stage in patches:
        originals[(module, attr)] = getattr(module, attr)
        setattr(module, attr, wrap(stage, originals[(module, attr)]))

    try:
        yield state
    finally:
        for module, attr in originals:
            setattr(module, attr, originals[(module, attr)])


def _resolve_video_path(topic: str, results: list) -> Path | None:
    from scripts.utils.slug import content_output_dir

    for item in results or []:
        video = item.get("video")
        if video and Path(video).exists():
            return Path(video).resolve()

    folder = content_output_dir({"nome": topic}, platform="youtube_dark")
    candidate = folder / "video_final.mp4"
    if candidate.exists():
        return candidate.resolve()

    return None


def run_test_video(topic: str, *, force: bool = False) -> Path:
    _banner("YouTube Dark — teste de 1 vídeo (free providers)")
    print(f"Tema: {topic}")
    print("Providers: Gemini+Groq | Wikimedia+Pixabay | Edge TTS")
    print(f"Etapas: {' → '.join(STAGE_ORDER)}")

    _load_env()
    _check_ffmpeg()
    _configure_free_providers()
    _preflight_keys()

    os.environ["PIPELINE_TOPIC_OVERRIDE"] = topic

    from scripts.pipeline.youtube_pipeline import run_youtube_pipeline

    with _stage_tracker() as state:
        try:
            results = run_youtube_pipeline(
                max_videos=1,
                auto_upload=False,
                production_mode=False,
                force=force,
            )
        except Exception as exc:
            stage = state.get("current", "unknown")
            print(f"\n❌ FALHA na etapa: {stage}")
            print(f"   Erro: {exc}")
            traceback.print_exc()
            raise SystemExit(1) from exc

    video_path = _resolve_video_path(topic, results)
    if not video_path:
        print("\n❌ FALHA na etapa: render")
        print("   Erro: pipeline concluiu sem gerar video_final.mp4")
        raise SystemExit(1)

    print("\n✅ SUCESSO — vídeo gerado:")
    print(f"   {video_path}")
    return video_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline YouTube Dark — um vídeo de teste (providers gratuitos)",
    )
    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help=f"Tema do vídeo (padrão: {DEFAULT_TOPIC!r})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessar mesmo se o tema já tiver saída anterior",
    )
    args = parser.parse_args()

    run_test_video(args.topic, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
