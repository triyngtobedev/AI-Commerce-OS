"""
Prompt builder — adapta templates de e-commerce para cada API de vídeo.

Todas as APIs free têm resolução limitada; removemos referências a 4K e
ajustamos negative prompts conforme suporte de cada provider.
"""

from __future__ import annotations

from typing import Literal, TypedDict

ApiName = Literal["falai", "replicate", "kling_web"]
I2VMovement = Literal["zoom", "rotate", "float", "reveal"]

_I2V_MOVEMENT_PROMPTS: dict[str, str] = {
    "zoom": "slow cinematic zoom in, product stays centered",
    "rotate": "camera orbits around product, 180 degrees, smooth",
    "float": "product gently floating, subtle up-down motion",
    "reveal": "dramatic light reveal, product emerges from darkness",
}

# Movimento I2V recomendado por categoria de produto (baseado em testes reais —
# ver analysis/test_results.md). Mantém alinhamento com _I2V_MOVEMENT_PROMPTS.
CATEGORY_MOVEMENT_MAP: dict[str, str] = {
    "tecnologia": "zoom",
    "casa": "float",
    "automotivo": "reveal",
    "moda": "rotate",
    "calcados": "rotate",
    "beleza": "float",
    "default": "zoom",
}


def get_best_movement(category: str) -> str:
    """
    Retorna o movimento I2V recomendado para a categoria do produto.

    A busca é case-insensitive; categorias desconhecidas (ou vazias) caem no
    default ``zoom``, que é o movimento mais seguro para e-commerce.

    Args:
        category: Categoria do produto (ex.: ``"Casa"``, ``"Automotivo"``).

    Returns:
        Nome do movimento (``zoom`` | ``rotate`` | ``float`` | ``reveal``).
    """
    return CATEGORY_MOVEMENT_MAP.get((category or "").strip().lower(), "zoom")

DEFAULT_NEGATIVE = (
    "blurry, distorted, low quality, watermark, overexposed, shaky camera, text overlay"
)

_QUALITY_REPLACEMENT = "sharp, high detail, crisp edges, photorealistic"


class PromptBundle(TypedDict):
    """Prompt positivo e negative prompt opcional."""

    prompt: str
    negative_prompt: str | None


def _base_sections(product_name: str, extra: str = "") -> dict[str, str]:
    """Monta seções comuns do template e-commerce (sem 4K)."""
    sections = {
        "product": f"[PRODUCT FOCUS]: {product_name} centered in frame",
        "lighting": "[LIGHTING]: studio lighting, soft shadows, clean background",
        "movement": "[MOVEMENT]: slow zoom-in / gentle 360 rotation",
        "quality": f"[QUALITY]: {_QUALITY_REPLACEMENT}",
    }
    if extra.strip():
        sections["extra"] = extra.strip()
    return sections


def _join_positive(sections: dict[str, str]) -> str:
    """Concatena seções em prompt positivo em inglês."""
    return "\n".join(sections.values())


def _inline_negative(positive: str, negative: str) -> str:
    """Incorpora negative prompt no texto positivo (APIs sem campo separado)."""
    return f"{positive}\n[Avoid]: {negative}"


def build_prompt(product_name: str, api: ApiName, *, extra: str = "") -> PromptBundle:
    """
    Retorna prompt adaptado às limitações de cada API.

    Args:
        product_name: Nome do produto em foco.
        api: Provider alvo — ``falai``, ``replicate`` ou ``kling_web``.
        extra: Descrição adicional opcional (sempre em inglês).

    Returns:
        Dict com ``prompt`` e ``negative_prompt`` (``None`` quando inline).
    """
    sections = _base_sections(product_name, extra)
    positive = _join_positive(sections)

    if api == "kling_web":
        return {"prompt": positive, "negative_prompt": DEFAULT_NEGATIVE}

    # falai e replicate: negative inline (sem campo dedicado confiável no free tier)
    return {
        "prompt": _inline_negative(positive, DEFAULT_NEGATIVE),
        "negative_prompt": None,
    }


def build_ecommerce_i2v_prompt(
    product_name: str,
    material: str | None = None,
    color: str | None = None,
    movement: I2VMovement = "zoom",
) -> PromptBundle:
    """
    Retorna prompt otimizado para I2V de produto e-commerce.

    Testado com lightricks/ltx-video no Replicate.
    """
    movement_text = _I2V_MOVEMENT_PROMPTS.get(movement, _I2V_MOVEMENT_PROMPTS["zoom"])

    detail_parts: list[str] = []
    if material:
        detail_parts.append(f"{material} material")
    if color:
        detail_parts.append(f"{color} color")
    detail = ", ".join(detail_parts)

    sections = {
        "product": (
            f"[PRODUCT FOCUS]: {product_name} centered in frame, "
            "commercial product photography, clean white studio background"
        ),
        "lighting": "[LIGHTING]: soft studio lighting, subtle shadows, high-key e-commerce look",
        "movement": f"[MOVEMENT]: {movement_text}",
        "quality": f"[QUALITY]: {_QUALITY_REPLACEMENT}, product details sharp and accurate",
    }
    if detail:
        sections["detail"] = f"[DETAIL]: {detail}, preserve exact product shape and color from input image"

    positive = _join_positive(sections)
    return {
        "prompt": _inline_negative(positive, DEFAULT_NEGATIVE),
        "negative_prompt": DEFAULT_NEGATIVE,
    }


_YOUTUBE_PLATFORM_STYLE = {
    "youtube": (
        "dark cinematic documentary, dramatic lighting, 16:9 landscape, "
        "atmospheric, film grain, moody shadows"
    ),
    "tiktok": (
        "vertical mobile video, clean product showcase, bright studio, "
        "9:16 portrait, social media aesthetic"
    ),
}

_SCENE_TIPO_SUFFIX: dict[str, str] = {
    "hook": "dramatic establishing shot, tension, slow push-in",
    "contexto": "historical context aerial wide, archival documentary feel",
    "desenvolvimento_1": "investigation documentary b-roll, research footage",
    "desenvolvimento_2": "historical event dramatic reenactment style",
    "revelacao": "dramatic reveal, cinematic spotlight, narrative climax",
    "consequencias": "impact consequences documentary, emotional weight",
    "impacto": "modern legacy impact, contrast past and present",
    "encerramento": "cinematic closing shot, atmospheric fade, contemplative",
}

_YOUTUBE_NEGATIVE = (
    "blurry, distorted, low quality, watermark, text overlay, "
    "cartoon, anime, bright cheerful, stock photo look, shaky handheld, "
    "overexposed, neon colors, product placement"
)


_VISUAL_TYPE_SUFFIX: dict[str, str] = {
    "historical_documentary": "archival war documentary footage, authentic period atmosphere",
    "geographic_explanation": "aerial map geography documentary, strategic overview",
    "emotional_moment": "intimate emotional documentary, human scale tragedy",
    "investigation": "research investigation documentary, documents and evidence",
    "dramatic_event": "dramatic historical event reenactment style, high tension",
    "general_narrative": "documentary cinematic b-roll",
}

_ANIMATION_CAMERA: dict[str, str] = {
    "archive_footage": "subtle film grain, archival camera drift",
    "map_movement": "slow pan across historical map",
    "ken_burns": "slow Ken Burns push on still photograph",
    "timeline": "gentle lateral drift, timeline narrative",
}


def build_scene_video_prompt(
    scene_description: str,
    scene_query: str,
    platform: str = "youtube",
    style: str = "cinematic",
    *,
    scene_tipo: str = "",
    emotion: str = "",
    visual_direction: dict | None = None,
) -> PromptBundle:
    """
    Prompt otimizado para cenas de vídeo YouTube Dark (T2V documental).

    Diferente do I2V de produto: tom dramático, cinematográfico, 16:9.
    """
    subject = (scene_query or scene_description or "historical documentary scene").strip()
    platform_key = "youtube" if platform in ("youtube", "youtube_dark") else platform
    platform_style = _YOUTUBE_PLATFORM_STYLE.get(platform_key, _YOUTUBE_PLATFORM_STYLE["youtube"])

    if visual_direction:
        scene_tipo = scene_tipo or visual_direction.get("section_key", "")
        emotion = emotion or visual_direction.get("emotion", "")

    tipo_suffix = _SCENE_TIPO_SUFFIX.get(scene_tipo, "documentary cinematic b-roll")
    emotion_clause = f", {emotion} mood" if emotion else ""

    visual_type = (visual_direction or {}).get("visual_type", "")
    animation = (visual_direction or {}).get("animation_strategy", "")
    type_suffix = _VISUAL_TYPE_SUFFIX.get(visual_type, "")
    camera_suffix = _ANIMATION_CAMERA.get(animation, "slow deliberate camera movement")

    sections = {
        "scene": f"[SCENE]: {subject}",
        "context": f"[CONTEXT]: {scene_description}".strip() if scene_description else "",
        "style": f"[STYLE]: {style}, {platform_style}{emotion_clause}",
        "camera": f"[CAMERA]: {tipo_suffix}, {camera_suffix}",
        "quality": f"[QUALITY]: {_QUALITY_REPLACEMENT}, photorealistic documentary footage",
    }
    if type_suffix:
        sections["visual_type"] = f"[VISUAL TYPE]: {type_suffix}"
    positive = _join_positive({k: v for k, v in sections.items() if v})
    return {
        "prompt": _inline_negative(positive, _YOUTUBE_NEGATIVE),
        "negative_prompt": _YOUTUBE_NEGATIVE,
    }


def build_from_description(
    description: str,
    api: ApiName,
    *,
    product_name: str | None = None,
) -> PromptBundle:
    """
    Atalho: extrai product_name da descrição se omitido.

    Args:
        description: Texto base do produto/cena (inglês recomendado).
        api: Provider alvo.
        product_name: Nome explícito do produto; default = primeira cláusula.
    """
    name = product_name or description.split(",")[0].strip() or "product"
    return build_prompt(name, api, extra=description)
