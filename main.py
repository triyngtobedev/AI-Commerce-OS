"""
AI-Commerce-OS

Entrada principal do sistema.
Suporta múltiplas plataformas:
  - tiktok_shop (padrão)
  - youtube_dark
"""

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from scripts.pipeline.product_pipeline import run_pipeline
from scripts.pipeline.youtube_pipeline import run_youtube_pipeline


def run_youtube_auth():
    """Executa fluxo OAuth interativo do YouTube."""

    from scripts.publisher.youtube_auth import run_interactive_oauth

    status = run_interactive_oauth()
    print(status.summary())

    return 0 if status.valid else 1


def run_youtube_validate():
    """Valida configuração OAuth do YouTube."""

    from scripts.publisher.youtube_auth import validate_credentials

    status = validate_credentials(test_connection=True)
    print(status.summary())

    return 0 if status.valid else 1


def run_youtube_analytics():
    """Exibe métricas e insights do canal YouTube."""

    from scripts.youtube.youtube_analytics import fetch_channel_insights

    print("\n📈 YouTube Analytics\n")

    result = fetch_channel_insights()

    if not result.get("configured"):

        print(
            f"❌ {result.get('error', 'Não configurado')}"
        )

        if result.get("missing"):
            print(
                f"   Variáveis ausentes: "
                f"{', '.join(result['missing'])}"
            )

        print(
            "\n   Configure com: python main.py --youtube-auth"
        )

        return 1

    if result.get("error"):

        print(f"❌ Erro: {result['error']}")
        return 1

    insights = result["insights"]

    print(f"Visualizações (28d): {insights['total_views']}")
    print(f"CTR médio: {insights['average_ctr']}%")
    print(f"Retenção média: {insights['average_retention']}%")
    print(
        f"Tempo médio de exibição: "
        f"{insights['average_view_duration']}s"
    )
    print(
        f"Crescimento de inscritos: "
        f"{insights['subscriber_growth']}"
    )

    if insights.get("best_performing_titles"):

        print("\nTítulos de melhor desempenho:")

        for title in insights["best_performing_titles"]:
            print(f"  • {title}")

    if insights.get("recommendations"):

        print("\nRecomendações de otimização:")

        for rec in insights["recommendations"]:
            print(f"  → {rec}")

    print()
    return 0


def run():
    parser = argparse.ArgumentParser(
        description="AI-Commerce-OS — Geração automática de conteúdo"
    )

    parser.add_argument(
        "--platform",
        choices=["tiktok_shop", "youtube_dark", "all"],
        default="tiktok_shop",
        help="Plataforma alvo (padrão: tiktok_shop)",
    )

    parser.add_argument(
        "--research",
        action="store_true",
        help="Pesquisar temas automaticamente (YouTube)",
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Publicar automaticamente no YouTube após produção",
    )

    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="Status de privacidade do upload YouTube",
    )

    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Máximo de vídeos a produzir",
    )

    parser.add_argument(
        "--youtube-auth",
        action="store_true",
        help="Configurar OAuth do YouTube interativamente",
    )

    parser.add_argument(
        "--youtube-validate",
        action="store_true",
        help="Validar credenciais OAuth do YouTube",
    )

    parser.add_argument(
        "--youtube-analytics",
        action="store_true",
        help="Exibir métricas e insights do canal YouTube",
    )

    args = parser.parse_args()

    if args.youtube_auth:
        sys.exit(run_youtube_auth())

    if args.youtube_validate:
        sys.exit(run_youtube_validate())

    if args.youtube_analytics:
        sys.exit(run_youtube_analytics())

    print("\n🚀 Iniciando AI-Commerce-OS\n")
    print(f"Plataforma: {args.platform}\n")

    all_results = []

    if args.platform in ("tiktok_shop", "all"):
        print("▶️ Pipeline TikTok Shop")
        tiktok_results = run_pipeline()
        all_results.extend(tiktok_results)

    if args.platform in ("youtube_dark", "all"):
        print("▶️ Pipeline YouTube Dark")
        max_videos = args.max_videos or 1
        youtube_results = run_youtube_pipeline(
            auto_research=args.research,
            max_videos=max_videos,
            auto_upload=args.upload,
            privacy_status=args.privacy,
        )
        all_results.extend(youtube_results)

    print("\n==============================")
    print("PROCESSO FINALIZADO")
    print(f"Conteúdos gerados: {len(all_results)}")
    print("==============================\n")


if __name__ == "__main__":
    run()
