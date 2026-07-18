"""
Rotas de analytics — sincronização e relatórios.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsSyncResponse(BaseModel):
    success: bool
    synced: int = 0
    failed: int = 0
    total_videos: int = 0
    last_sync: str | None = None
    message: str = ""


class AnalyticsReportResponse(BaseModel):
    success: bool
    report_path: str
    content: str


@router.post("/sync", response_model=AnalyticsSyncResponse)
async def sync_analytics(days: int = 28) -> AnalyticsSyncResponse:
    """Sincroniza métricas do YouTube Analytics para database/analytics.json."""
    from scripts.analytics.youtube_analytics import sync_all_videos

    result = sync_all_videos(days=days)
    return AnalyticsSyncResponse(
        success=result.get("success", False),
        synced=result.get("synced", 0),
        failed=result.get("failed", 0),
        total_videos=result.get("total_videos", 0),
        last_sync=result.get("last_sync"),
        message=result.get("message", ""),
    )


@router.post("/report", response_model=AnalyticsReportResponse)
async def generate_report(days: int = 7, sync_first: bool = True) -> AnalyticsReportResponse:
    """Gera relatório semanal e salva em reports/relatorio_YYYY-MM-DD.md."""
    from scripts.analytics.report import generate_report, save_report

    content = generate_report(days=days, sync_first=sync_first)
    path = save_report(content)

    return AnalyticsReportResponse(
        success=True,
        report_path=str(path),
        content=content,
    )
