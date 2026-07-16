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


def run_youtube_branding(apply: bool = False):
    """Gera assets de marca e aplica branding no canal YouTube."""

    from pathlib import Path

    from scripts.core.brand_profile import (
        BRAND_ASSETS,
        YOUTUBE_DARK_CHANNEL_DESCRIPTION,
    )
    from scripts.publisher.youtube_channel_branding import apply_channel_branding
    from scripts.youtube.channel_assets import generate_all_assets
    from scripts.youtube.upload_image_prep import prepare_brand_upload_assets

    print("\n🎨 Identidade Visual — Projeto Atlas\n")

    BRAND_ASSETS.mkdir(parents=True, exist_ok=True)

    desc_path = BRAND_ASSETS / "channel_description.txt"
    desc_path.write_text(
        YOUTUBE_DARK_CHANNEL_DESCRIPTION.strip() + "\n",
        encoding="utf-8",
    )

    print("Gerando assets visuais...")
    assets = generate_all_assets()

    for name, path in assets.items():
        print(f"  ✅ {name}: {path}")

    upload_assets = prepare_brand_upload_assets()
    print("\nCópias prontas para upload no YouTube (originais preservados):")
    for name, path in upload_assets.items():
        print(f"  ✅ {name}: {path}")

    print(f"  ✅ channel_description: {desc_path}")

    identity_path = BRAND_ASSETS / "IDENTITY.md"
    identity_path.write_text(
        _build_identity_doc(),
        encoding="utf-8",
    )
    print(f"  ✅ identity_doc: {identity_path}")

    if not apply:
        print(
            "\n💡 Assets gerados. Para aplicar no canal via API, execute:\n"
            "   python main.py --youtube-branding --apply\n"
        )
        return 0

    print("\nAplicando branding no canal via API...\n")
    result = apply_channel_branding(dry_run=False)
    print(result.summary())

    return 0 if result.success else 1


def _build_identity_doc() -> str:
    """Documenta o conceito visual da marca."""

    return """\
# Projeto Atlas — Identidade Visual

## Conceito

**Projeto Atlas** é um canal de documentários sobre história, mistério e ciência.
O nome evoca o titã que sustentou o mundo — uma metáfora para a missão do canal:
revelar os eventos que sustentam e moldam a compreensão humana do passado.

## Posicionamento

- **Nicho:** Documentários narrados sobre fatos históricos reais
- **Tom:** Autoridade documental com curiosidade genuína
- **Público:** Entusiastas de história, ciência e mistérios não resolvidos (PT-BR)
- **Diferencial:** Pesquisa rigorosa, narrativa envolvente, produção cinematográfica

## Paleta de Cores

| Elemento | RGB | Hex | Uso |
|----------|-----|-----|-----|
| Fundo | (8, 12, 24) | #080C18 | Backgrounds, banner |
| Primária | (12, 18, 32) | #0C1220 | Overlays, gradientes |
| Destaque | (255, 183, 3) | #FFB703 | Bússola, barras, CTAs |
| Texto | (255, 255, 255) | #FFFFFF | Títulos e corpo |

## Símbolo

Bússola estilizada com a letra **A** central — representa exploração,
orientação no desconhecido e a busca por respostas documentadas.

## Tipografia

- Títulos: Arial Bold
- Corpo: Arial Regular

## Assets

| Arquivo | Dimensão | Uso |
|---------|----------|-----|
| profile_picture.png | 800×800 | Foto de perfil (circular) |
| banner.png | 2560×1440 | Banner do canal |
| channel_description.txt | — | Descrição oficial do canal |

## Área Segura do Banner

Conteúdo principal centralizado em 1546×423 px (visível em TV, desktop e mobile).
"""


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

    parser.add_argument(
        "--youtube-branding",
        action="store_true",
        help="Gerar assets de identidade visual do canal YouTube",
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar branding no canal via API (usar com --youtube-branding)",
    )

    args = parser.parse_args()

    if args.youtube_auth:
        sys.exit(run_youtube_auth())

    if args.youtube_validate:
        sys.exit(run_youtube_validate())

    if args.youtube_analytics:
        sys.exit(run_youtube_analytics())

    if args.youtube_branding:
        sys.exit(run_youtube_branding(apply=args.apply))

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
