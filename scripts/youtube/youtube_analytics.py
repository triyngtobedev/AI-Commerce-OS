"""
YouTube Analytics API

Integração modular com YouTube Analytics para otimização
automática de conteúdo futuro (títulos, descrições, tags, etc.).
"""

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from scripts.publisher.youtube_auth import (
    build_google_credentials,
    validate_credentials,
)


@dataclass
class VideoAnalytics:
    """Métricas de desempenho de um vídeo."""

    video_id: str
    title: str = ""
    views: int = 0
    impressions: int = 0
    ctr: float = 0.0
    average_view_duration_seconds: float = 0.0
    average_view_percentage: float = 0.0
    estimated_minutes_watched: float = 0.0
    likes: int = 0
    comments: int = 0
    subscribers_gained: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelAnalytics:
    """Métricas agregadas do canal."""

    channel_id: str
    channel_title: str = ""
    total_views: int = 0
    total_impressions: int = 0
    average_ctr: float = 0.0
    average_view_duration_seconds: float = 0.0
    subscribers_gained: int = 0
    estimated_minutes_watched: float = 0.0
    video_count: int = 0
    top_videos: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationInsights:
    """
    Insights derivados para otimização futura.

    Alimenta decisões sobre títulos, descrições, tags e thumbnails.
    """

    best_performing_titles: List[str] = field(default_factory=list)
    average_ctr: float = 0.0
    average_retention: float = 0.0
    average_view_duration: float = 0.0
    total_views: int = 0
    subscriber_growth: int = 0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class YouTubeAnalyticsClient:
    """
    Cliente modular para YouTube Analytics API v2.

    Reutiliza credenciais OAuth do módulo youtube_auth.
    """

    def __init__(self):
        self._credentials = None
        self._youtube = None
        self._analytics = None
        self._channel_id = None

    def is_configured(self) -> bool:
        """Verifica se credenciais estão configuradas."""

        return validate_credentials().configured

    def _ensure_services(self):
        """Inicializa serviços da API sob demanda."""

        if self._analytics is not None:
            return

        try:
            from googleapiclient.discovery import build
        except ImportError as error:
            raise ImportError(
                "google-api-python-client não instalado. "
                "Execute: pip install google-api-python-client"
            ) from error

        self._credentials = build_google_credentials()

        self._youtube = build(
            "youtube",
            "v3",
            credentials=self._credentials,
        )

        self._analytics = build(
            "youtubeAnalytics",
            "v2",
            credentials=self._credentials,
        )

        self._channel_id = self._resolve_channel_id()

    def _resolve_channel_id(self) -> str:
        """Obtém ID do canal autenticado."""

        response = self._youtube.channels().list(
            part="id,snippet",
            mine=True,
        ).execute()

        items = response.get("items", [])

        if not items:
            raise ValueError(
                "Nenhum canal encontrado para a conta autenticada"
            )

        return items[0]["id"]

    def get_channel_info(self) -> Dict[str, str]:
        """Retorna informações básicas do canal."""

        self._ensure_services()

        response = self._youtube.channels().list(
            part="snippet,statistics",
            mine=True,
        ).execute()

        channel = response["items"][0]

        return {
            "channel_id": channel["id"],
            "title": channel["snippet"]["title"],
            "subscribers": channel.get(
                "statistics", {}
            ).get("subscriberCount", "0"),
            "total_views": channel.get(
                "statistics", {}
            ).get("viewCount", "0"),
        }

    def get_video_analytics(
        self,
        video_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> VideoAnalytics:
        """
        Obtém métricas de um vídeo específico.

        Métricas: views, CTR, retenção, impressões, tempo médio.
        """

        self._ensure_services()

        if end_date is None:
            end_date = date.today()

        if start_date is None:
            start_date = end_date - timedelta(days=28)

        metrics = ",".join([
            "views",
            "impressions",
            "impressionClickThroughRate",
            "averageViewDuration",
            "averageViewPercentage",
            "estimatedMinutesWatched",
            "likes",
            "comments",
            "subscribersGained",
        ])

        response = self._analytics.reports().query(
            ids=f"channel=={self._channel_id}",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics=metrics,
            dimensions="video",
            filters=f"video=={video_id}",
        ).execute()

        rows = response.get("rows", [])
        headers = [
            h["name"]
            for h in response.get("columnHeaders", [])
        ]

        title = self._get_video_title(video_id)

        if not rows:
            return VideoAnalytics(
                video_id=video_id,
                title=title,
            )

        data = dict(zip(headers[1:], rows[0][1:]))

        return VideoAnalytics(
            video_id=video_id,
            title=title,
            views=int(data.get("views", 0)),
            impressions=int(data.get("impressions", 0)),
            ctr=round(
                float(data.get("impressionClickThroughRate", 0)) * 100,
                2,
            ),
            average_view_duration_seconds=round(
                float(data.get("averageViewDuration", 0)),
                1,
            ),
            average_view_percentage=round(
                float(data.get("averageViewPercentage", 0)),
                1,
            ),
            estimated_minutes_watched=round(
                float(data.get("estimatedMinutesWatched", 0)),
                1,
            ),
            likes=int(data.get("likes", 0)),
            comments=int(data.get("comments", 0)),
            subscribers_gained=int(
                data.get("subscribersGained", 0)
            ),
        )

    def get_channel_analytics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_top_videos: int = 5,
    ) -> ChannelAnalytics:
        """
        Obtém métricas agregadas do canal.

        Inclui CTR, retenção, impressões, visualizações e crescimento.
        """

        self._ensure_services()

        if end_date is None:
            end_date = date.today()

        if start_date is None:
            start_date = end_date - timedelta(days=28)

        channel_info = self.get_channel_info()

        metrics = ",".join([
            "views",
            "impressions",
            "impressionClickThroughRate",
            "averageViewDuration",
            "estimatedMinutesWatched",
            "subscribersGained",
        ])

        response = self._analytics.reports().query(
            ids=f"channel=={self._channel_id}",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics=metrics,
        ).execute()

        rows = response.get("rows", [])
        headers = [
            h["name"]
            for h in response.get("columnHeaders", [])
        ]

        totals = {}

        if rows:
            totals = dict(zip(headers, rows[0]))

        top_videos = self._get_top_videos(
            start_date,
            end_date,
            max_top_videos,
        )

        return ChannelAnalytics(
            channel_id=self._channel_id,
            channel_title=channel_info["title"],
            total_views=int(totals.get("views", 0)),
            total_impressions=int(totals.get("impressions", 0)),
            average_ctr=round(
                float(totals.get("impressionClickThroughRate", 0)) * 100,
                2,
            ),
            average_view_duration_seconds=round(
                float(totals.get("averageViewDuration", 0)),
                1,
            ),
            subscribers_gained=int(
                totals.get("subscribersGained", 0)
            ),
            estimated_minutes_watched=round(
                float(totals.get("estimatedMinutesWatched", 0)),
                1,
            ),
            video_count=len(top_videos),
            top_videos=top_videos,
        )

    def get_optimization_insights(
        self,
        days: int = 28,
    ) -> OptimizationInsights:
        """
        Gera insights para otimização de conteúdo futuro.

        Analisa desempenho histórico e produz recomendações para
        títulos, descrições, tags, thumbnails e estratégia.
        """

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        channel = self.get_channel_analytics(
            start_date=start_date,
            end_date=end_date,
        )

        recommendations = []
        best_titles = []

        for video in channel.top_videos:
            if video.get("title"):
                best_titles.append(video["title"])

        if channel.average_ctr < 3.0:
            recommendations.append(
                "CTR abaixo de 3% — teste títulos mais impactantes "
                "e thumbnails com maior contraste"
            )
        elif channel.average_ctr >= 5.0:
            recommendations.append(
                "CTR acima de 5% — replique padrões dos títulos "
                "e thumbnails dos vídeos de melhor desempenho"
            )

        avg_retention = 0.0

        if channel.top_videos:
            retentions = [
                v.get("average_view_percentage", 0)
                for v in channel.top_videos
            ]
            avg_retention = round(
                sum(retentions) / len(retentions),
                1,
            )

        if avg_retention < 40:
            recommendations.append(
                "Retenção baixa — revise ganchos iniciais e "
                "estrutura narrativa dos primeiros 30 segundos"
            )

        if channel.subscribers_gained > 0:
            recommendations.append(
                f"Canal ganhou {channel.subscribers_gained} inscritos "
                "no período — mantenha frequência de publicação"
            )

        if not recommendations:
            recommendations.append(
                "Dados insuficientes — publique mais vídeos para "
                "gerar insights de otimização"
            )

        return OptimizationInsights(
            best_performing_titles=best_titles[:3],
            average_ctr=channel.average_ctr,
            average_retention=avg_retention,
            average_view_duration=channel.average_view_duration_seconds,
            total_views=channel.total_views,
            subscriber_growth=channel.subscribers_gained,
            recommendations=recommendations,
        )

    def _get_video_title(self, video_id: str) -> str:
        """Obtém título de um vídeo via Data API."""

        response = self._youtube.videos().list(
            part="snippet",
            id=video_id,
        ).execute()

        items = response.get("items", [])

        if items:
            return items[0]["snippet"]["title"]

        return ""

    def _get_top_videos(
        self,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Lista vídeos com melhor desempenho no período."""

        metrics = ",".join([
            "views",
            "impressions",
            "impressionClickThroughRate",
            "averageViewPercentage",
            "averageViewDuration",
        ])

        response = self._analytics.reports().query(
            ids=f"channel=={self._channel_id}",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics=metrics,
            dimensions="video",
            sort="-views",
            maxResults=limit,
        ).execute()

        rows = response.get("rows", [])
        headers = [
            h["name"]
            for h in response.get("columnHeaders", [])
        ]

        top_videos = []

        for row in rows:
            data = dict(zip(headers, row))
            video_id = data.get("video", "")

            top_videos.append({
                "video_id": video_id,
                "title": self._get_video_title(video_id),
                "views": int(data.get("views", 0)),
                "impressions": int(data.get("impressions", 0)),
                "ctr": round(
                    float(data.get("impressionClickThroughRate", 0)) * 100,
                    2,
                ),
                "average_view_percentage": round(
                    float(data.get("averageViewPercentage", 0)),
                    1,
                ),
                "average_view_duration": round(
                    float(data.get("averageViewDuration", 0)),
                    1,
                ),
            })

        return top_videos


def fetch_channel_insights(
    days: int = 28,
) -> Dict[str, Any]:
    """
    Atalho para obter insights de otimização do canal.

    Retorna dict serializável para integração com pipeline/métricas.
    """

    client = YouTubeAnalyticsClient()

    if not client.is_configured():

        status = validate_credentials()

        return {
            "configured": False,
            "error": "Credenciais YouTube não configuradas",
            "missing": status.missing,
        }

    try:
        insights = client.get_optimization_insights(days=days)

        return {
            "configured": True,
            "insights": insights.to_dict(),
        }

    except Exception as error:

        return {
            "configured": True,
            "error": str(error),
        }
