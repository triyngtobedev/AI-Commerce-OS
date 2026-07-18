#!/usr/bin/env python3
"""
⚠️ DESENVOLVIMENTO APENAS — NÃO USAR NO PC DO DONO.

Executa o pipeline lofi_dark **localmente** (IA + TTS + FFmpeg no seu PC).
Serve só para debug de agentes/desenvolvedores.

Comando oficial (dono / produção):
    python scripts/cloud/gerar_video.py --topic "Seu tema" --template lofi_dark
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

DEFAULT_TOPIC = "O Mistério da Explosão de Tunguska"


def main() -> int:
    print(
        "\n⚠️  scripts/dev/gerar_lofi_dark.py — APENAS DESENVOLVIMENTO\n"
        "   Produção: python scripts/cloud/gerar_video.py "
        '--topic "..." --template lofi_dark\n'
    )

    parser = argparse.ArgumentParser(
        description="[DEV] Pipeline lofi_dark local — não usar em produção",
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("PIPELINE_TOPIC_OVERRIDE", DEFAULT_TOPIC),
        help="Nome exato do tema (database/topics_source.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessar mesmo se o tema já tiver vídeo gerado",
    )
    args = parser.parse_args()

    os.environ["PIPELINE_ROTEIRO_TEMPLATE"] = "lofi_dark"
    if args.topic:
        os.environ["PIPELINE_TOPIC_OVERRIDE"] = args.topic

    from scripts.pipeline.youtube_pipeline import run_youtube_pipeline

    print("\n🌙 [DEV] Pipeline lofi_dark local")
    print(f"   Tema: {args.topic}")
    print("   Template: lofi_dark (15–25 min, footage genérico)\n")

    results = run_youtube_pipeline(
        max_videos=1,
        force_topic_name=args.topic,
        force=args.force,
    )

    if not results:
        print("\n❌ Nenhum vídeo produzido (execução local de debug).\n")
        return 1

    from scripts.utils.slug import content_output_dir

    folder = content_output_dir({"nome": args.topic}, platform="youtube_dark")
    print(f"\n✅ [DEV] Pasta: {folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
