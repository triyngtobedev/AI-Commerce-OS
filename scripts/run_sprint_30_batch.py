#!/usr/bin/env python3
"""
Batch Sprint 30 — produz 5–10 vídeos YouTube Dark com métricas JSONL.

Uso:
  python3 scripts/run_sprint_30_batch.py [--max-videos 8] [--force]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

# Garante flags Sprint 30 ativas para o batch
os.environ.setdefault("SPRINT30_ENABLED", "true")
os.environ.setdefault("SPRINT30_VISUAL_SCORE", "true")
os.environ.setdefault("SPRINT30_THUMBNAIL_AB", "true")
os.environ.setdefault("SPRINT30_AUDIO_LAYER", "true")
os.environ.setdefault("SPRINT30_RETENTION_CONTROLLER", "true")
os.environ.setdefault("SPRINT30_METRICS", "true")


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch Sprint 30 — YouTube Dark")
    parser.add_argument("--max-videos", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    from scripts.audio.populate_audio_library import populate_audio_library
    from scripts.pipeline.youtube_pipeline import run_youtube_pipeline

    print("\n🎬 Sprint 30 Batch — populando biblioteca de áudio...")
    populate_audio_library()

    print(f"\n▶️ Produzindo até {args.max_videos} vídeos (sem smoke test)...")
    results = run_youtube_pipeline(
        auto_research=False,
        max_videos=args.max_videos,
        auto_upload=False,
        production_mode=False,
        force=args.force,
    )

    produced = sum(1 for item in results if item.get("video"))
    print(f"\n✅ Batch concluído: {produced}/{len(results)} vídeos com arquivo final")
    print("📊 Métricas: sprint_30_metrics.jsonl")

    return 0 if produced > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
