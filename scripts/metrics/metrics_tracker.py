"""
Metrics Tracker

Registra métricas de produção e publicação
para otimização futura de conteúdo.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

METRICS_FILE = Path("database/metrics.json")


def _load_metrics() -> List[Dict[str, Any]]:
    """Carrega histórico de métricas."""

    if not METRICS_FILE.exists():

        return []


    with open(
        METRICS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)


    return data if isinstance(data, list) else []



def _save_metrics(records: List[Dict[str, Any]]):
    """Persiste métricas."""

    METRICS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    with open(
        METRICS_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=4,
        )



def record_production(
    result: Dict[str, Any],
    upload_result: Optional[Dict[str, Any]] = None,
):
    """
    Registra métricas de uma produção de conteúdo.

    Args:
        result: PipelineResult serializado
        upload_result: Resultado do upload (opcional)
    """

    records = _load_metrics()


    subject = result.get("produto", {})

    record = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "platform": result.get(
            "platform",
            "unknown"
        ),
        "subject_name": subject.get("nome", ""),
        "subject_category": subject.get(
            "categoria",
            ""
        ),
        "score_ia": result.get(
            "analise", {}
        ).get("score"),
        "score_opportunity": result.get(
            "oportunidade", {}
        ).get("score_venda"),
        "acao": result.get("acao"),
        "angulo": result.get(
            "estrategia", {}
        ).get("angulo"),
        "titulo": result.get(
            "conteudo", {}
        ).get("titulo"),
        "duracao": result.get(
            "conteudo", {}
        ).get("duracao"),
        "video_path": result.get("video"),
        "status": "produced",
    }


    if upload_result:

        record["upload_status"] = upload_result.get(
            "status"
        )

        record["video_id"] = upload_result.get(
            "video_id"
        )

        record["video_url"] = upload_result.get(
            "url"
        )

        record["upload_message"] = upload_result.get(
            "message"
        )

        if upload_result.get("status") == "UPLOADED":

            record["status"] = "published"

        elif upload_result.get("status") == "SKIPPED":

            record["status"] = "produced_not_uploaded"


    records.append(record)

    _save_metrics(records)


    print(
        f"📊 Métrica registrada: {record['subject_name']}"
    )

    if upload_result:
        upload_status = upload_result.get("status", "N/A")
        print(f"   Upload: {upload_status}")

        if upload_result.get("video_id"):
            print(
                f"   Video ID: {upload_result['video_id']}"
            )

        if upload_result.get("url"):
            print(f"   URL: {upload_result['url']}")

        if upload_result.get("message"):
            print(
                f"   Detalhe: {upload_result['message']}"
            )

    _try_attach_analytics(record)

    return record


def _try_attach_analytics(record: Dict[str, Any]):
    """Anexa insights do YouTube Analytics quando disponível."""

    if record.get("platform") != "youtube_dark":
        return

    if not record.get("video_id"):
        return

    try:
        from scripts.youtube.youtube_analytics import (
            YouTubeAnalyticsClient,
        )

        client = YouTubeAnalyticsClient()

        if not client.is_configured():
            return

        analytics = client.get_video_analytics(
            record["video_id"]
        )

        record["analytics"] = analytics.to_dict()

        records = _load_metrics()

        if records and records[-1].get("video_id") == record.get("video_id"):
            records[-1]["analytics"] = record["analytics"]
            _save_metrics(records)

    except Exception:
        pass



def get_metrics_summary(
    platform: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retorna resumo das métricas registradas.
    """

    records = _load_metrics()


    if platform:

        records = [
            r
            for r in records
            if r.get("platform") == platform
        ]


    total = len(records)

    published = sum(
        1
        for r in records
        if r.get("status") == "published"
    )


    avg_score = 0

    scores = [
        r.get("score_opportunity", 0)
        for r in records
        if r.get("score_opportunity")
    ]

    if scores:

        avg_score = round(
            sum(scores) / len(scores),
            1,
        )


    return {
        "total_produzidos": total,
        "total_publicados": published,
        "score_medio": avg_score,
        "plataforma": platform or "todas",
    }
