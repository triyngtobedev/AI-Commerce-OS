#!/usr/bin/env python3
"""
Gera um vídeo YouTube completo com template lofi_dark (estilo Filosofatos).

Uso (na raiz do repo):
    python gerar_lofi_dark.py
    python gerar_lofi_dark.py --topic "O Mistério da Explosão de Tunguska"
    python gerar_lofi_dark.py --topic "SEU TEMA" --force
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
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
    parser = argparse.ArgumentParser(
        description="Gera vídeo YouTube com roteiro_template=lofi_dark",
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

    import scripts.pipeline.youtube_pipeline as pipeline_module

    original_strategy = pipeline_module.generate_youtube_strategy

    def patched_strategy(topic, analysis, opportunity):
        strategy = original_strategy(topic, analysis, opportunity)
        strategy["roteiro_template"] = "lofi_dark"
        strategy["duracao_alvo"] = "20 minutos"
        return strategy

    pipeline_module.generate_youtube_strategy = patched_strategy
    try:
        print("\n🌙 Pipeline lofi_dark")
        print(f"   Tema: {args.topic}")
        print("   Template: lofi_dark (15–25 min, footage genérico)")
        print("   (primeira execução pode levar bastante tempo)\n")

        results = pipeline_module.run_youtube_pipeline(
            max_videos=1,
            force_topic_name=args.topic,
            force=args.force,
        )
    finally:
        pipeline_module.generate_youtube_strategy = original_strategy

    if not results:
        print(
            "\n❌ Nenhum vídeo produzido.\n"
            "   Verifique no .env: GEMINI_API_KEY ou GROQ_API_KEY\n"
            "   FFmpeg instalado e no PATH.\n"
        )
        return 1

    from scripts.utils.slug import content_output_dir

    folder = content_output_dir({"nome": args.topic}, platform="youtube_dark")
    video = folder / "video_final.mp4"
    thumb = folder / "thumbnail.jpg"

    print("\n✅ Produção concluída")
    print(f"   Pasta: {folder}")
    if video.exists():
        print(f"   Vídeo:  {video}")
    if thumb.exists():
        print(f"   Thumb:  {thumb}")

    meta = folder / "script.json"
    if meta.exists():
        print(f"   Roteiro: {meta}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
