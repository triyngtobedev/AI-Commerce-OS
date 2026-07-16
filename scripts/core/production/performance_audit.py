"""
Auditoria de performance ao final da execução do pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from scripts.core.production.logger import get_logger
from scripts.core.production.pipeline_state import STAGE_ORDER


# Mapeamento de etapas para categorias de tempo
_STAGE_CATEGORIES = {
    "collect": "setup",
    "analysis": "ai",
    "strategy": "ai",
    "script": "ai",
    "timeline": "ai",
    "media": "media_search",
    "audio": "audio",
    "render": "render",
    "export": "export",
    "validate": "validation",
    "upload": "upload",
    "manifest": "export",
    "report": "export",
}


def _aggregate_timings(step_timings: dict) -> dict:
    categories: Dict[str, float] = {}

    for stage, seconds in step_timings.items():
        cat = _STAGE_CATEGORIES.get(stage, "other")
        categories[cat] = categories.get(cat, 0) + seconds

    return {k: round(v, 3) for k, v in categories.items()}


def _find_bottlenecks(step_timings: dict, threshold_ratio: float = 0.25) -> List[dict]:
    if not step_timings:
        return []

    total = sum(step_timings.values())
    if total <= 0:
        return []

    bottlenecks = []
    for stage, seconds in sorted(step_timings.items(), key=lambda x: -x[1]):
        ratio = seconds / total
        if ratio >= threshold_ratio:
            bottlenecks.append({
                "stage": stage,
                "seconds": round(seconds, 3),
                "percent": round(ratio * 100, 1),
            })

    return bottlenecks


def _generate_suggestions(
    aggregated: dict,
    bottlenecks: list,
    *,
    providers_used: Optional[list] = None,
) -> List[str]:
    suggestions = []

    ai_time = aggregated.get("ai", 0)
    media_time = aggregated.get("media_search", 0)
    render_time = aggregated.get("render", 0)
    upload_time = aggregated.get("upload", 0)

    if ai_time > media_time and ai_time > render_time:
        suggestions.append(
            "IA é o maior gargalo — considere cache de roteiro/estratégia para temas similares."
        )

    if media_time > 120:
        suggestions.append(
            "Busca de mídia lenta — verifique chaves de API (Pixabay, Pexels, Wikimedia) "
            "e paralelização de downloads."
        )

    if render_time > 300:
        suggestions.append(
            "Renderização demorada — considere reduzir resolução de cenas ou usar preset ffmpeg mais rápido."
        )

    if upload_time > 180:
        suggestions.append(
            "Upload lento — verifique conexão e tamanho do vídeo final."
        )

    for bn in bottlenecks[:2]:
        stage = bn["stage"]
        if stage == "media":
            suggestions.append(
                "Paralelizar busca e download de assets por cena pode reduzir tempo de mídia."
            )
        elif stage in ("script", "strategy", "analysis"):
            suggestions.append(
                f"Etapa '{stage}' consome {bn['percent']}% do tempo — cache de IA pode ajudar."
            )

    if providers_used and "none" in providers_used:
        suggestions.append(
            "Algumas buscas de mídia retornaram vazio — configure PIXABAY_API_KEY e PEXELS_API_KEY."
        )

    if not suggestions:
        suggestions.append("Pipeline equilibrado — nenhum gargalo crítico detectado.")

    return suggestions


def generate_performance_report(
    output_dir: Path,
    pipeline_state: dict,
    *,
    extra_metrics: Optional[dict] = None,
) -> dict:
    """
    Gera relatório de performance e salva em performance_report.json.
    """

    logger = get_logger("performance")
    step_timings = pipeline_state.get("step_timings", {})
    total_time = round(sum(step_timings.values()), 3)

    aggregated = _aggregate_timings(step_timings)
    bottlenecks = _find_bottlenecks(step_timings)
    providers = pipeline_state.get("providers_used", [])

    report = {
        "total_seconds": total_time,
        "step_timings": step_timings,
        "aggregated": {
            "tempo_ia": aggregated.get("ai", 0),
            "tempo_busca_midia": aggregated.get("media_search", 0),
            "tempo_downloads": aggregated.get("media_search", 0) * 0.4,  # estimativa
            "tempo_render": aggregated.get("render", 0),
            "tempo_upload": aggregated.get("upload", 0),
            "tempo_audio": aggregated.get("audio", 0),
            "tempo_export": aggregated.get("export", 0),
        },
        "bottlenecks": bottlenecks,
        "suggestions": _generate_suggestions(aggregated, bottlenecks, providers_used=providers),
        "providers_used": providers,
        "stages_order": STAGE_ORDER,
    }

    if extra_metrics:
        report["extra"] = extra_metrics

    path = output_dir / "performance_report.json"
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    logger.success(
        f"Relatório de performance gerado — total: {total_time:.1f}s, "
        f"gargalos: {len(bottlenecks)}"
    )

    return report
