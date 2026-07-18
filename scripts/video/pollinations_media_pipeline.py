"""
Pollinations Media Pipeline — geração de imagens de cena por IA (gratuita).

Modo alternativo ao stock, ativado por CONTENT_MODE=persona (ou "ai"/
"pollinations"). Em vez de baixar mídia genérica do Pexels/Pixabay, gera uma
imagem única e cinematográfica para CADA cena usando a API gratuita da
Pollinations.ai (https://image.pollinations.ai/prompt/{prompt}) — sem chave.

As imagens são salvas como scene-NN.jpg, integrando-se ao render scene-aware:
o scene_renderer aplica automaticamente Ken Burns / parallax nessas imagens,
mantendo o movimento e segurando a retenção.
"""

from __future__ import annotations

import os
from pathlib import Path

from scripts.utils.slug import content_output_dir
from scripts.video.media_providers.pollinations_provider import (
    generate_pollinations_image,
)
from scripts.video.media_quality import (
    MIN_AI_IMAGE_HEIGHT,
    MIN_AI_IMAGE_WIDTH,
    validate_image_file,
)
from scripts.core.visual_director_engine import direct_scene_visual
from src.prompt_builder import build_scene_image_prompt


# CONTENT_MODE que ativam a geração por IA (Pollinations).
_PERSONA_MODES = {"persona", "ai", "pollinations"}


def content_mode() -> str:
    """Modo de conteúdo atual (CONTENT_MODE do .env)."""

    return os.getenv("CONTENT_MODE", "stock").strip().lower()


def should_use_persona() -> bool:
    """True quando o modo de geração por IA (Pollinations) está ativo."""

    return content_mode() in _PERSONA_MODES


def _dimensions_for_platform(platform: str) -> tuple[int, int]:
    """Vertical (9:16) para TikTok; horizontal (16:9) para YouTube."""

    if platform and platform != "youtube_dark":
        return 1080, 1920

    return 1920, 1080


def _scene_prompt(scene: dict, platform: str = "youtube_dark") -> str:
    """Monta prompt cinematográfico YouTube Dark a partir da cena."""

    visual = (scene.get("visual") or "").strip()
    narracao = (scene.get("narracao") or "").strip()
    query = (scene.get("query") or scene.get("busca") or "").strip()

    visual_direction = scene.get("visual_direction")
    if not visual_direction and (visual or narracao):
        visual_direction = direct_scene_visual(scene).to_dict()

    bundle = build_scene_image_prompt(
        scene_description=visual or narracao[:160],
        scene_query=query or visual or narracao[:120],
        platform=platform,
        scene_tipo=scene.get("tipo", ""),
        emotion=scene.get("emotion", ""),
        visual_direction=visual_direction,
        max_length=280,
    )
    return bundle["prompt"]


def _clear_stock_leftovers(images_folder: Path, videos_folder: Path) -> None:
    """Remove mídia stock antiga preservando as imagens IA (scene-*)."""

    if videos_folder.exists():
        for old_file in videos_folder.glob("*"):
            try:
                old_file.unlink()
            except OSError as error:
                print(f"⚠️ Não foi possível remover {old_file}: {error}")

    if images_folder.exists():
        for old_file in images_folder.glob("*"):
            if old_file.name.startswith("scene-"):
                continue
            try:
                old_file.unlink()
            except OSError as error:
                print(f"⚠️ Não foi possível remover {old_file}: {error}")


def generate_persona_media(subject, scenes) -> list:
    """
    Gera imagens de cena por IA (Pollinations) e salva como scene-NN.jpg.

    Segue o padrão de limpeza segura: só remove os assets stock antigos após a
    primeira imagem ser confirmada, preservando o fallback caso a IA falhe.
    Retorna a lista de arquivos criados.
    """

    platform = subject.get("_output_platform", "")
    assets = content_output_dir(subject, platform=platform) / "assets"
    images_folder = assets / "images"
    videos_folder = assets / "videos"
    images_folder.mkdir(parents=True, exist_ok=True)

    width, height = _dimensions_for_platform(platform)

    # Piso de validação relaxado para IA: o scene_renderer normaliza e faz
    # upscale automático, então aceitamos qualquer imagem >= 1024x576 (16:9)
    # sem disparar o fallback. Para vertical (9:16), invertemos os eixos.
    if width >= height:
        floor_w, floor_h = MIN_AI_IMAGE_WIDTH, MIN_AI_IMAGE_HEIGHT
    else:
        floor_w, floor_h = MIN_AI_IMAGE_HEIGHT, MIN_AI_IMAGE_WIDTH

    scene_list = (
        scenes.get("cenas", []) if isinstance(scenes, dict) else (scenes or [])
    )

    generated: list[Path] = []
    stock_cleared = False

    print(
        f"[POLLINATIONS] Gerando {len(scene_list)} imagens de cena por IA "
        f"({width}x{height})..."
    )

    for index, scene in enumerate(scene_list):
        scene_num = index + 1
        output_path = images_folder / f"scene-{scene_num:02d}.jpg"
        prompt = _scene_prompt(scene, platform=platform)

        ok = generate_pollinations_image(prompt, output_path, width=width, height=height)

        if ok:
            valid, reason = validate_image_file(
                output_path,
                min_width=floor_w,
                min_height=floor_h,
            )
            if not valid:
                print(f"  ⚠️ Cena {scene_num}: imagem IA rejeitada ({reason})")
                if output_path.exists():
                    output_path.unlink()
                ok = False

        if not ok:
            print(f"[POLLINATIONS] Cena {scene_num} falhou — fallback preservado.")
            continue

        # Primeira imagem confirmada: agora é seguro limpar o stock antigo.
        if not stock_cleared:
            _clear_stock_leftovers(images_folder, videos_folder)
            stock_cleared = True

        generated.append(output_path)
        print(f"🎨 Cena {scene_num}: imagem IA gerada — {output_path.name}")

    print(f"[POLLINATIONS] {len(generated)}/{len(scene_list)} imagens geradas.")

    return generated
