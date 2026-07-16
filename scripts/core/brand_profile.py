"""
Perfil de marca do canal YouTube Dark.

Centraliza identidade visual para thumbnails, vídeo e overlays.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class BrandProfile:
    """Identidade visual de um canal."""

    channel_name: str
    tagline: str
    primary_color: Tuple[int, int, int]
    accent_color: Tuple[int, int, int]
    text_color: Tuple[int, int, int]
    background_color: Tuple[int, int, int]
    font_bold: str
    font_body: str
    watermark_opacity: float = 0.35
    thumbnail_width: int = 1280
    thumbnail_height: int = 720


ROOT = Path(__file__).resolve().parents[2]
BRAND_ASSETS = ROOT / "assets" / "brand"


YOUTUBE_DARK_BRAND = BrandProfile(
    channel_name="Projeto Atlas",
    tagline="História · Mistério · Ciência",
    primary_color=(12, 18, 32),
    accent_color=(255, 183, 3),
    text_color=(255, 255, 255),
    background_color=(8, 12, 24),
    font_bold="arialbd.ttf",
    font_body="arial.ttf",
    watermark_opacity=0.4,
)

YOUTUBE_DARK_CHANNEL_DESCRIPTION = """\
Bem-vindo ao Projeto Atlas — o canal onde história, mistério e ciência se encontram em documentários narrados com profundidade e rigor.

Aqui você encontra histórias reais que mudaram o curso da humanidade: explosões inexplicáveis na Sibéria, civilizações perdidas, epidemias que redefiniram continentes, personalidades que desafiaram seu tempo e descobertas científicas que ainda intrigam pesquisadores.

Cada vídeo é produzido com pesquisa documental, narrativa envolvente e edição cinematográfica — pensado para quem busca respostas, não especulação. Fatos verificados, contexto histórico e a curiosidade que move a ciência.

📌 O que você encontra aqui:
• Documentários sobre eventos históricos e mistérios não resolvidos
• Análises de civilizações antigas, guerras e descobertas científicas
• Narrativas em português com qualidade de produção profissional
• Novos episódios toda semana

🔔 Inscreva-se e ative o sininho para não perder nenhum episódio.

—

Palavras-chave: documentário, história, mistério, ciência, curiosidades, fatos históricos, mistérios não resolvidos, civilizações antigas, descobertas científicas, educação, documentário brasileiro.
"""


def get_brand(platform_id: str = "youtube_dark") -> BrandProfile:
    """Retorna perfil de marca da plataforma."""

    if platform_id == "youtube_dark":
        return YOUTUBE_DARK_BRAND

    return YOUTUBE_DARK_BRAND


def resolve_font(font_name: str, size: int):
    """Carrega fonte com fallbacks para Windows."""

    from PIL import ImageFont

    candidates = [
        BRAND_ASSETS / font_name,
        Path("C:/Windows/Fonts") / font_name,
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]

    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue

    return ImageFont.load_default()
