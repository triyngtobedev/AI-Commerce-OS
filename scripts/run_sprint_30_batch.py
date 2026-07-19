#!/usr/bin/env python3
"""
Batch Sprint 30 — validação controlada do pipeline YouTube Dark.

Uso:
  python scripts/run_sprint_30_batch.py --max-videos 2
  python scripts/run_sprint_30_batch.py --max-videos 2 --revalidate --force

Fluxo:
  1. Preflight health (get_client().health())
  2. Produção resumível (--production)
  3. Métricas em database/sprint_30_metrics.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

# Ativa Sprint 30 para este processo (flags + métricas no pipeline).
os.environ.setdefault("SPRINT30", "true")
os.environ.setdefault("FOOTAGE_FIRST", "true")
os.environ.setdefault("RETENTION_CONTROLLER", "true")


def _banner(title: str) -> None:
    line = "═" * 56
    print(f"\n{line}\n {title}\n{line}")


def _run_preflight(*, skip_health: bool) -> dict:
    from scripts.ai.router import get_client

    health = get_client().health()
    print(json.dumps(health, indent=2, ensure_ascii=False))

    if skip_health:
        print("\n⚠️ Preflight ignorado (--skip-health)")
        return health

    if not health.get("ready_for_batch"):
        missing = ", ".join(health.get("missing_required", []))
        print(f"\n❌ Ambiente não pronto para batch. Faltando: {missing}")
        sys.exit(1)

    print("\n✅ Preflight OK — iniciando batch Sprint 30")
    return health


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch Sprint 30 — YouTube Dark")
    parser.add_argument(
        "--max-videos",
        type=int,
        default=2,
        help="Quantidade de vídeos (default: 2 para validação)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocessa tópicos já produzidos",
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Pula preflight (não recomendado)",
    )
    parser.add_argument(
        "--research",
        action="store_true",
        help="Pesquisa novos tópicos antes do batch",
    )
    parser.add_argument(
        "--revalidate",
        action="store_true",
        help="Reavalia exports existentes (sem regerar vídeo)",
    )
    args = parser.parse_args()

    _banner("Sprint 30 — Preflight")
    _run_preflight(skip_health=args.skip_health)

    from scripts.sprint30.metrics import (
        get_batch_id,
        revalidate_export_folder,
        summarize_metrics_file,
    )
    from scripts.pipeline.youtube_pipeline import run_youtube_pipeline
    from scripts.data_sources.youtube.topic_collector import collect_topics
    from scripts.youtube.topic_selector import select_next_topics, collect_processed_topic_names
    from scripts.core.platform_config import YOUTUBE_DARK
    from scripts.utils.slug import content_output_dir

    batch_id = get_batch_id()

    if args.revalidate:
        _banner(f"Sprint 30 — Revalidação {batch_id} ({args.max_videos} vídeo(s))")
        topics = collect_topics()
        processed = collect_processed_topic_names(platform=YOUTUBE_DARK.id)
        selected = select_next_topics(
            topics,
            max_videos=args.max_videos,
            platform=YOUTUBE_DARK.id,
            processed_names=processed,
            force=args.force,
        )
        revalidated = 0
        for topic in selected:
            folder = content_output_dir(topic, platform=YOUTUBE_DARK.id)
            record = revalidate_export_folder(topic, folder)
            if record:
                revalidated += 1
                print(
                    f"✅ Revalidado: {topic.get('nome')} "
                    f"(quality={record.get('quality_score')}, "
                    f"retention={record.get('retention_predicted_score')})"
                )
            else:
                print(f"⚠️ Sem video_final.mp4: {topic.get('nome')}")

        _banner("Sprint 30 — Resumo")
        summary = summarize_metrics_file()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"\nRevalidados: {revalidated}/{len(selected)}")
        return 0 if revalidated > 0 else 1

    _banner(f"Sprint 30 — Batch {batch_id} ({args.max_videos} vídeo(s))")

    results = run_youtube_pipeline(
        auto_research=args.research,
        max_videos=args.max_videos,
        auto_upload=False,
        production_mode=True,
        force=args.force,
    )

    videos_ok = sum(1 for item in results if item.get("video"))
    _banner("Sprint 30 — Resumo")
    summary = summarize_metrics_file()

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nConteúdos gerados: {len(results)}")
    print(f"Vídeos com arquivo final: {videos_ok}")
    print(f"Métricas: {summary.get('metrics_path')}")

    if videos_ok == 0:
        print("\n❌ Batch concluiu sem vídeos finais.")
        return 1

    if summary.get("failed"):
        print(f"\n⚠️ {summary['failed']} falha(s) registrada(s) no batch.")
        return 1 if videos_ok < args.max_videos else 0

    print("\n✅ Batch Sprint 30 concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
