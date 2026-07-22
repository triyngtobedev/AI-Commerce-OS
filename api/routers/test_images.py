"""
Test endpoint para validação visual de busca de imagens + prompt Flux.

POST /api/v1/test/images
  Body: { topic, cenas: [{ titulo, narracao, busca }] }
  Retorna metadados da busca em Pexels/Pixabay/Wikimedia + prompt Flux,
  sem baixar nada nem gerar imagens.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status

from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter(prefix="/test", tags=["test"])

# ── Schemas ─────────────────────────────────────────────────────────────


class TestScene(BaseModel):
    titulo: str = Field(description="Título da cena (só para identificação)")
    narracao: str = Field(description="Texto da narração da cena")
    busca: str = Field(description="Query de busca visual (ex: roman legions barbarian invasion)")


class TestImagesRequest(BaseModel):
    topic: str = Field(description="Tema central do vídeo", example="A queda do Império Romano")
    cenas: list[TestScene] = Field(min_length=1, max_length=10)


class ProviderResult(BaseModel):
    provider: str
    query_original: str
    query_usada: str
    url: str | None = None
    resolucao: str | None = None
    preview_url: str | None = None
    erro: str | None = None


class SceneResult(BaseModel):
    titulo: str
    flux_prompt: str | None = None
    flux_negative_prompt: str | None = None
    resultados: list[ProviderResult]
    tempo_segundos: float


class TestImagesResponse(BaseModel):
    topic: str
    cenas: list[SceneResult]
    tempo_total_segundos: float


# ── Providers ───────────────────────────────────────────────────────────

_TIMEOUT = 15

# Mapeamento de temas históricos → queries stock (mesmo dos providers)
_HISTORICAL_STOCK_MAP = {
    "rome": "ancient rome",
    "roman": "ancient rome",
    "egypt": "ancient egypt",
    "egito": "ancient egypt",
    "greece": "ancient greece",
    "grecia": "ancient greece",
    "greek": "ancient greece",
    "medieval": "medieval castle",
    "temple": "ancient temple",
    "templo": "ancient temple",
    "pyramid": "egypt pyramid",
    "piramide": "egypt pyramid",
    "pirâmide": "egypt pyramid",
    "soldier": "roman soldier",
    "soldiers": "soldiers army",
    "war": "war battle soldiers",
    "battle": "battle soldiers",
    "king": "king crown throne",
    "queen": "queen crown",
    "emperor": "emperor crown",
    "sword": "sword weapon",
    "ship": "ship ocean sailing",
    "horse": "horse riding",
    "castle": "medieval castle",
    "ruins": "ancient ruins",
    "ruinas": "ancient ruins",
    "forest": "forest nature",
    "floresta": "forest nature",
    "desert": "desert landscape",
    "deserto": "desert landscape",
    "mountains": "mountain landscape",
    "montanha": "mountain landscape",
    "ocean": "ocean sea waves",
    "city": "city architecture",
    "cidade": "city architecture",
    "map": "world map",
    "mapa": "world map",
    "fire": "fire flame",
    "fogo": "fire flame",
    "explosion": "explosion fire",
    "meteor": "meteor sky",
}


def _simplify_for_stock(query: str) -> str:
    query_lower = query.strip().lower()
    if not query_lower:
        return query
    if query_lower in _HISTORICAL_STOCK_MAP:
        return _HISTORICAL_STOCK_MAP[query_lower]
    words = query.strip().split()
    for word in words:
        word_lower = word.lower().strip(".,!?;:")
        if word_lower in _HISTORICAL_STOCK_MAP:
            return _HISTORICAL_STOCK_MAP[word_lower]
    return " ".join(words[:3]).strip()


def _search_pexels(query: str) -> list[dict]:
    import os

    from scripts.video.pexels_provider import search_pexels

    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return [{"provider": "pexels", "query_original": query, "erro": "PEXELS_API_KEY não configurada"}]

    query_usada = _simplify_for_stock(query)
    results: list[dict] = []
    try:
        data = search_pexels(query_usada, orientation="landscape", per_page=5)
        photos = data.get("photos", [])
        if photos:
            for p in photos[:3]:
                src = p.get("src", {})
                results.append({
                    "provider": "pexels",
                    "query_original": query,
                    "query_usada": query_usada,
                    "url": src.get("original") or src.get("large") or "",
                    "resolucao": f"{p.get('width', '?')}x{p.get('height', '?')}",
                    "preview_url": src.get("medium") or src.get("small") or "",
                })
        else:
            results.append({"provider": "pexels", "query_original": query, "query_usada": query_usada, "erro": "sem resultados"})
    except Exception as e:
        results.append({"provider": "pexels", "query_original": query, "query_usada": query_usada, "erro": str(e)})

    return results


def _search_pixabay(query: str) -> list[dict]:
    from scripts.video.pixabay_provider import search_pixabay

    query_usada = _simplify_for_stock(query)
    results: list[dict] = []
    try:
        data = search_pixabay(query_usada, orientation="horizontal", per_page=5)
        photos = data.get("photos", [])
        if photos:
            for p in photos[:3]:
                results.append({
                    "provider": "pixabay",
                    "query_original": query,
                    "query_usada": query_usada,
                    "url": p.get("largeImageURL") or p.get("webformatURL") or "",
                    "resolucao": f"{p.get('imageWidth', '?')}x{p.get('imageHeight', '?')}",
                    "preview_url": p.get("previewURL") or "",
                })
        else:
            results.append({"provider": "pixabay", "query_original": query, "query_usada": query_usada, "erro": "sem resultados"})
    except Exception as e:
        results.append({"provider": "pixabay", "query_original": query, "query_usada": query_usada, "erro": str(e)})

    return results


def _search_wikimedia(query: str) -> list[dict]:
    from scripts.video.media_providers.wikimedia_provider import search_wikimedia

    # Wikimedia mantém query completa (indexa conteúdo histórico)
    results: list[dict] = []
    try:
        data = search_wikimedia(query, limit=5)
        photos = data.get("photos", [])
        if photos:
            for p in photos[:3]:
                src = p.get("src", {})
                results.append({
                    "provider": "wikimedia",
                    "query_original": query,
                    "query_usada": query,
                    "url": src.get("original") or "",
                    "resolucao": f"{p.get('width', '?')}x{p.get('height', '?')}",
                    "preview_url": src.get("thumb") or src.get("medium", src.get("small", "")),
                })
        else:
            results.append({"provider": "wikimedia", "query_original": query, "query_usada": query, "erro": "sem resultados"})
    except Exception as e:
        results.append({"provider": "wikimedia", "query_original": query, "query_usada": query, "erro": str(e)})

    return results


def _build_flux_prompt(topic: str, scene: TestScene) -> tuple[str | None, str | None]:
    """Constrói o prompt que seria enviado ao Flux Schnell para esta cena."""
    try:
        from src.prompt_builder import build_scene_image_prompt
        from scripts.video.query_localizer import localize_search_query

        scene_query = localize_search_query(scene.busca, append_documentary=False)
        # Enriquece com o tópico (igual ao fix do Problema 1)
        scene_description = f"{topic}: {scene.busca}"
        if scene.narracao and len(scene.narracao) > 10:
            scene_description = f"{scene_description} - {scene.narracao[:100]}"

        bundle = build_scene_image_prompt(
            scene_description=scene_description,
            scene_query=scene_query,
            platform="youtube_dark",
            scene_tipo="contexto",
            emotion="curiosity",
            max_length=280,
        )
        return bundle.get("prompt"), bundle.get("negative_prompt")
    except Exception as e:
        return None, None


def _search_all_providers(query: str) -> list[dict]:
    """Busca em todos os providers em paralelo e retorna resultados."""
    results: list[dict] = []

    # Pexels e Pixabay primeiro (stock footage, maior chance)
    results.extend(_search_pexels(query))

    results.extend(_search_pixabay(query))

    # Wikimedia terciário (arquivo histórico)
    results.extend(_search_wikimedia(query))

    return results


# ── Endpoint ────────────────────────────────────────────────────────────


@router.post("/images", response_model=TestImagesResponse)
async def test_images(payload: TestImagesRequest) -> TestImagesResponse:
    """
    Testa busca de imagens para cada cena e exibe o prompt do Flux.

    Para cada cena:
      1. Gera queries em Pexels, Pixabay e Wikimedia
      2. Constrói o prompt Flux (sem chamar a API — só inspeção)
      3. Retorna URLs, providers, resoluções + prompt

    Timeout total: 30s por cena.
    """
    started = time.monotonic()
    scene_results: list[SceneResult] = []

    for i, cena in enumerate(payload.cenas):
        scene_start = time.monotonic()
        query = cena.busca.strip() or cena.titulo.strip()

        # Busca em todos os providers
        resultados = _search_all_providers(query)

        # Constrói prompt Flux
        flux_prompt, flux_negative = _build_flux_prompt(payload.topic, cena)

        scene_results.append(SceneResult(
            titulo=cena.titulo,
            flux_prompt=flux_prompt,
            flux_negative_prompt=flux_negative,
            resultados=[ProviderResult(**r) for r in resultados],
            tempo_segundos=round(time.monotonic() - scene_start, 2),
        ))

    return TestImagesResponse(
        topic=payload.topic,
        cenas=scene_results,
        tempo_total_segundos=round(time.monotonic() - started, 2),
    )


@router.get("/images", include_in_schema=False)
async def test_images_get():
    """GET existe só pra não dar 404 se baterem sem querer."""
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={
            "erro": "Use POST /api/v1/test/images com JSON body",
            "exemplo": {
                "topic": "A queda do Império Romano",
                "cenas": [
                    {"titulo": "O declínio militar", "narracao": "Legiões enfraquecidas...", "busca": "roman legions barbarian invasion"},
                ],
            },
        },
        status_code=status.HTTP_400_BAD_REQUEST,
    )
