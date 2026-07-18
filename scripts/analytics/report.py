#!/usr/bin/env python3
"""
Gera relatório semanal de desempenho dos vídeos.

Uso:
    python scripts/analytics/report.py
    python scripts/analytics/report.py --days 7
    python scripts/analytics/report.py --output reports/relatorio_2026-07-18.md
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.analytics.video_registry import get_videos_since
from scripts.analytics.youtube_analytics import get_analytics_store, sync_all_videos

REPORTS_DIR = Path("reports")


def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "0s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _aggregate_metrics(videos: List[Dict[str, Any]], analytics: Dict[str, Any]) -> Dict[str, Any]:
    total_views = 0
    total_watch_minutes = 0.0
    ctr_values: List[float] = []
    retention_values: List[float] = []
    rows: List[Dict[str, Any]] = []

    analytics_videos = analytics.get("videos", {})

    for video in videos:
        video_id = video.get("video_id", "")
        metrics = analytics_videos.get(video_id, {})

        views = int(metrics.get("views", 0))
        ctr = float(metrics.get("ctr", 0))
        retention = float(metrics.get("average_view_percentage", 0))
        watch_seconds = float(metrics.get("average_view_duration_seconds", 0))
        watch_minutes = float(metrics.get("estimated_minutes_watched", 0))

        total_views += views
        total_watch_minutes += watch_minutes
        if ctr > 0:
            ctr_values.append(ctr)
        if retention > 0:
            retention_values.append(retention)

        rows.append({
            "title": video.get("title") or metrics.get("title") or video.get("topic", "Sem título"),
            "topic": video.get("topic", ""),
            "template": video.get("template", ""),
            "video_url": video.get("video_url", ""),
            "views": views,
            "ctr": ctr,
            "retention": retention,
            "avg_watch": watch_seconds,
            "published_at": video.get("published_at", ""),
        })

    rows.sort(key=lambda r: r["views"], reverse=True)

    return {
        "video_count": len(videos),
        "total_views": total_views,
        "total_watch_minutes": round(total_watch_minutes, 1),
        "avg_ctr": round(sum(ctr_values) / len(ctr_values), 4) if ctr_values else 0.0,
        "avg_retention": round(sum(retention_values) / len(retention_values), 2) if retention_values else 0.0,
        "rows": rows,
    }


def generate_report(*, days: int = 7, sync_first: bool = True) -> str:
    """
    Gera relatório em Markdown dos vídeos dos últimos N dias.
    """
    if sync_first:
        print("🔄 Sincronizando métricas do YouTube...")
        sync_all_videos()

    videos = get_videos_since(days=days)
    analytics = get_analytics_store()
    stats = _aggregate_metrics(videos, analytics)

    now = datetime.now(timezone.utc)
    period_start = now.strftime("%Y-%m-%d")
    report_date = now.strftime("%Y-%m-%d")

    lines = [
        f"# Relatório Semanal — {report_date}",
        "",
        f"**Período:** últimos {days} dias",
        f"**Vídeos publicados:** {stats['video_count']}",
        f"**Total de views:** {stats['total_views']:,}",
        f"**Watch time total:** {stats['total_watch_minutes']:,.1f} min",
        f"**CTR médio:** {stats['avg_ctr']:.2%}",
        f"**Retenção média:** {stats['avg_retention']:.1f}%",
        "",
    ]

    if not stats["rows"]:
        lines.extend([
            "_Nenhum vídeo publicado no período._",
            "",
            f"_Última sincronização: {analytics.get('last_sync', 'nunca')}_",
        ])
        return "\n".join(lines)

    lines.extend([
        "## Vídeos da semana",
        "",
        "| Título | Views | CTR | Retenção | Watch médio | Link |",
        "|--------|------:|----:|---------:|------------:|------|",
    ])

    for row in stats["rows"]:
        title = (row["title"][:50] + "…") if len(row["title"]) > 50 else row["title"]
        url = row["video_url"] or "—"
        lines.append(
            f"| {title} | {row['views']:,} | {row['ctr']:.1%} | "
            f"{row['retention']:.1f}% | {_format_duration(row['avg_watch'])} | {url} |"
        )

    if stats["rows"]:
        best = stats["rows"][0]
        lines.extend([
            "",
            "## Destaque da semana",
            "",
            f"**{best['title']}** — {best['views']:,} views, "
            f"CTR {best['ctr']:.1%}, retenção {best['retention']:.1f}%",
            "",
        ])

    lines.append(f"_Gerado em {now.isoformat()}_")
    return "\n".join(lines)


def save_report(content: str, output_path: Path | None = None) -> Path:
    """Salva relatório em reports/relatorio_YYYY-MM-DD.md"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = REPORTS_DIR / f"relatorio_{date_str}.md"

    output_path.write_text(content, encoding="utf-8")
    print(f"📄 Relatório salvo: {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório semanal de vídeos YouTube")
    parser.add_argument("--days", type=int, default=7, help="Janela em dias (padrão: 7)")
    parser.add_argument("--output", type=str, default="", help="Caminho do arquivo de saída")
    parser.add_argument("--no-sync", action="store_true", help="Não sincronizar métricas antes")
    parser.add_argument("--print", action="store_true", dest="print_only", help="Só imprimir, não salvar")
    args = parser.parse_args()

    report = generate_report(days=args.days, sync_first=not args.no_sync)

    if args.print_only:
        print(report)
        return 0

    output = Path(args.output) if args.output else None
    path = save_report(report, output)
    print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
