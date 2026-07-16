"""
Visual Media Engine — busca e geração de mídia por cena.

Cadeia de fallback por cena:
  1. Pexels/Pixabay — vídeo HD relevante (validado)
  2. Pexels/Pixabay — foto stock HD
  3. Pollinations IA — imagem gratuita
  4. Pollinations IA — vídeo (se POLLINATIONS_API_KEY configurada)
  5. Pollinations IA — segunda tentativa de imagem com prompt alternativo
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.video.pexels_provider import search_pexels
from scripts.video.media_providers.pixabay_provider import search_pixabay
from scripts.video.media_providers.pollinations_provider import (
    generate_pollinations_image,
    generate_pollinations_video,
)
from scripts.video.media_providers.relevance import (
    MIN_ACCEPTABLE_QUALITY_SCORE,
    MIN_PHOTO_RELEVANCE_SCORE,
    MIN_RELEVANCE_SCORE,
    best_video_score,
    pick_ranked_photos,
    pick_ranked_videos,
    score_photo,
    score_video,
)
from scripts.video.media_downloader import (
    download_file,
    select_photo_url,
    select_video_file_with_fallback,
)
from scripts.video.media_quality import (
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_HEIGHT_FALLBACK,
    MIN_IMAGE_WIDTH,
    MIN_IMAGE_WIDTH_FALLBACK,
    MIN_VIDEO_HEIGHT,
    MIN_VIDEO_HEIGHT_FALLBACK,
    MIN_VIDEO_WIDTH,
    MIN_VIDEO_WIDTH_FALLBACK,
    validate_image_file,
    validate_video_file,
)


def _output_folder(subject):
    from scripts.utils.slug import content_output_dir

    platform = subject.get("_output_platform")
    return content_output_dir(subject, platform=platform)


def _has_media(media: dict) -> bool:
    return bool(media.get("videos") or media.get("photos"))


_CINEMATIC_SUFFIX = {
    "hook": "dramatic cinematic establishing shot documentary 4k",
    "contexto": "historical documentary aerial cinematic atmosphere",
    "desenvolvimento_1": "documentary investigation cinematic footage",
    "desenvolvimento_2": "historical event dramatic cinematic b-roll",
    "revelacao": "dramatic reveal cinematic documentary close",
    "consequencias": "impact consequences documentary cinematic",
    "impacto": "legacy modern impact cinematic documentary",
    "encerramento": "cinematic closing atmospheric documentary",
}


def _enrich_search_query(busca: str, tipo: str, fallback: str = "") -> list[str]:
    """
    Gera variações de busca cinematográficas baseadas na cena.
    Retorna queries em ordem de prioridade (sem duplicatas).
    """

    queries = []
    base = busca.strip()
    if base:
        queries.append(base)

    suffix = _CINEMATIC_SUFFIX.get(tipo, "documentary cinematic footage 4k")
    if base:
        enriched = f"{base} {suffix}"
        if enriched not in queries:
            queries.append(enriched)

    if fallback and fallback not in queries:
        queries.append(fallback.strip())

    if tipo and tipo not in queries:
        tipo_query = f"{tipo.replace('_', ' ')} {suffix}"
        if tipo_query not in queries:
            queries.append(tipo_query)

    return [q for q in queries if q]


def _merge_media(target: dict, source: dict) -> None:
    seen_videos = {video.get("id") for video in target.get("videos", []) if video.get("id")}
    seen_photos = {photo.get("id") for photo in target.get("photos", []) if photo.get("id")}

    for video in source.get("videos", []):
        vid = video.get("id")
        if vid and vid in seen_videos:
            continue
        if vid:
            seen_videos.add(vid)
        target.setdefault("videos", []).append(video)

    for photo in source.get("photos", []):
        pid = photo.get("id")
        if pid and pid in seen_photos:
            continue
        if pid:
            seen_photos.add(pid)
        target.setdefault("photos", []).append(photo)


def _search_all_providers(query: str) -> tuple[dict, str]:
    """Busca e combina resultados de Pexels + Pixabay."""

    merged = {"videos": [], "photos": []}
    providers = []

    for provider_name, search_fn in (
        ("pexels", search_pexels),
        ("pixabay", search_pixabay),
    ):
        media = search_fn(query)
        if _has_media(media):
            providers.append(provider_name)
            _merge_media(merged, media)

    source = "+".join(providers) if providers else "none"
    return merged, source


def _download_scene_video(video: dict, path: Path) -> bool:
    url, min_w, min_h = select_video_file_with_fallback(video)
    if not url:
        return False

    try:
        if path.exists():
            path.unlink()

        download_file(url, path)

        for attempt_min_w, attempt_min_h in (
            (min_w, min_h),
            (MIN_VIDEO_WIDTH_FALLBACK, MIN_VIDEO_HEIGHT_FALLBACK),
        ):
            valid, reason = validate_video_file(
                path,
                min_width=attempt_min_w,
                min_height=attempt_min_h,
            )
            if valid:
                return True

        print(f"  ⚠️ Vídeo rejeitado ({reason}): {path.name}")
        if path.exists():
            path.unlink()
        return False

    except Exception as error:
        print(f"Erro baixando vídeo da cena: {error}")
        if path.exists():
            path.unlink()
        return False


def _download_scene_photo(photo: dict, path: Path) -> bool:
    url = select_photo_url(photo, min_width=MIN_IMAGE_WIDTH)
    if not url:
        return False

    try:
        if path.exists():
            path.unlink()

        download_file(url, path)

        for attempt_min_w, attempt_min_h in (
            (MIN_IMAGE_WIDTH, MIN_IMAGE_HEIGHT),
            (MIN_IMAGE_WIDTH_FALLBACK, MIN_IMAGE_HEIGHT_FALLBACK),
        ):
            valid, reason = validate_image_file(
                path,
                min_width=attempt_min_w,
                min_height=attempt_min_h,
            )
            if valid:
                return True

        print(f"  ⚠️ Imagem rejeitada ({reason}): {path.name}")
        if path.exists():
            path.unlink()
        return False

    except Exception as error:
        print(f"Erro baixando imagem da cena: {error}")
        if path.exists():
            path.unlink()
        return False


def _try_stock_videos(
    query: str,
    media: dict,
    scene_video: Path,
    used_ids: set,
) -> tuple[bool, dict | None, float]:
    """Tenta baixar vídeos stock em ordem de relevância e qualidade."""

    candidates = pick_ranked_videos(query, media.get("videos", []), used_ids, limit=8)

    for video in candidates:
        quality_score = score_video(query, video)
        if quality_score < MIN_ACCEPTABLE_QUALITY_SCORE:
            continue

        if _download_scene_video(video, scene_video):
            return True, video, round(quality_score, 3)

    return False, None, 0.0


def _try_stock_photos(
    query: str,
    media: dict,
    scene_image: Path,
    used_ids: set,
) -> tuple[bool, dict | None]:
    """Tenta baixar fotos stock em ordem de relevância."""

    candidates = pick_ranked_photos(query, media.get("photos", []), used_ids, limit=5)

    for photo in candidates:
        photo_score = score_photo(query, photo)
        if photo_score < MIN_PHOTO_RELEVANCE_SCORE:
            continue
        if _download_scene_photo(photo, scene_image):
            return True, photo

    return False, None


def _try_ai_image(prompt: str, scene_image: Path, suffix: str = "") -> bool:
    ai_prompt = f"{prompt}, documentary cinematic scene{suffix}"
    if not generate_pollinations_image(ai_prompt, scene_image):
        return False

    valid, reason = validate_image_file(scene_image)
    if not valid:
        print(f"  ⚠️ Imagem IA rejeitada ({reason})")
        if scene_image.exists():
            scene_image.unlink()
        return False

    return True


def _try_ai_video(prompt: str, scene_video: Path) -> bool:
    ai_prompt = f"{prompt}, documentary cinematic footage"
    if not generate_pollinations_video(ai_prompt, scene_video):
        return False

    valid, reason = validate_video_file(scene_video, min_duration=2.0)
    if not valid:
        print(f"  ⚠️ Vídeo IA rejeitado ({reason})")
        if scene_video.exists():
            scene_video.unlink()
        return False

    return True


def _resolve_scene_media(
    scene_num: int,
    query_item: dict,
    scene_video: Path,
    scene_image: Path,
    used_ids: set,
) -> dict:
    """Resolve mídia para uma cena com fallback completo."""

    busca = query_item.get("busca", "")
    fallback = query_item.get("busca_fallback", "")
    tipo = query_item.get("tipo", "")

    result = {
        "scene": scene_num,
        "tipo": tipo,
        "query": busca,
        "query_enriched": busca,
        "source": "none",
        "media_type": "none",
        "saved": False,
        "quality_score": 0.0,
    }

    search_queries = _enrich_search_query(busca, tipo, fallback)

    media_by_query: dict[str, tuple[dict, str]] = {}
    for query in search_queries:
        media_by_query[query] = _search_all_providers(query)

    stock_video_found = False

    for query in search_queries:
        media, source = media_by_query[query]
        if not media.get("videos"):
            continue

        top_score = best_video_score(query, media.get("videos", []), used_ids)
        if top_score < MIN_RELEVANCE_SCORE:
            print(
                f"  ⚠️ Cena {scene_num}: relevância baixa ({top_score:.2f}) "
                f"para '{query}' — ignorando resultados genéricos"
            )
            continue

        saved, chosen, quality_score = _try_stock_videos(
            query, media, scene_video, used_ids
        )
        if saved and chosen:
            vid = chosen.get("id")
            if vid:
                used_ids.add(vid)
            stock_video_found = True
            result.update({
                "saved": True,
                "media_type": "video",
                "source": f"{source}:{query}",
                "query_enriched": query,
                "quality_score": quality_score,
            })
            print(
                f"🎬 Cena {scene_num} ({tipo}): vídeo HD "
                f"(score {quality_score}) — {source}"
            )
            return result

    if not stock_video_found:
        for query in search_queries:
            media, source = media_by_query[query]
            if not media.get("photos"):
                continue

            top_photo_score = max(
                (score_photo(query, photo) for photo in media.get("photos", [])),
                default=0.0,
            )
            if top_photo_score < MIN_PHOTO_RELEVANCE_SCORE:
                print(
                    f"  ⚠️ Cena {scene_num}: fotos irrelevantes para '{query}' "
                    f"(score {top_photo_score:.2f})"
                )
                continue

            saved, chosen = _try_stock_photos(query, media, scene_image, used_ids)
            if saved and chosen:
                pid = chosen.get("id")
                if pid:
                    used_ids.add(pid)
                result.update({
                    "saved": True,
                    "media_type": "image",
                    "source": f"{source}:{query}",
                    "query_enriched": query,
                    "quality_score": round(score_photo(query, chosen), 3),
                })
                print(f"🖼️ Cena {scene_num} ({tipo}): imagem stock — {source}")
                return result

    if _try_ai_image(busca, scene_image):
        result.update({"saved": True, "media_type": "ai_image", "source": "pollinations:image"})
        print(f"🤖 Cena {scene_num} ({tipo}): imagem IA (Pollinations)")
        return result

    if _try_ai_video(busca, scene_video):
        result.update({"saved": True, "media_type": "ai_video", "source": "pollinations:video"})
        print(f"🤖 Cena {scene_num} ({tipo}): vídeo IA (Pollinations)")
        return result

    if _try_ai_image(f"{busca}, {tipo}", scene_image, ", atmospheric wide shot"):
        result.update({"saved": True, "media_type": "ai_image_retry", "source": "pollinations:image:retry"})
        print(f"🤖 Cena {scene_num} ({tipo}): imagem IA (retry)")
        return result

    print(f"❌ Cena {scene_num}: nenhuma mídia disponível")
    return result


def run_visual_media_pipeline(subject, scenes, queries) -> str:
    """
    Pipeline de mídia scene-aware com seleção por relevância e fallback IA.
    Salva arquivos como scene-01.mp4, scene-02.jpg, etc.
    """

    folder = _output_folder(subject) / "assets"
    videos_folder = folder / "videos"
    images_folder = folder / "images"
    videos_folder.mkdir(parents=True, exist_ok=True)
    images_folder.mkdir(parents=True, exist_ok=True)

    used_ids: set = set()
    results = []

    for i, query_item in enumerate(queries):
        scene_num = i + 1
        scene_video = videos_folder / f"scene-{scene_num:02d}.mp4"
        scene_image = images_folder / f"scene-{scene_num:02d}.jpg"

        result = _resolve_scene_media(
            scene_num,
            query_item,
            scene_video,
            scene_image,
            used_ids,
        )
        results.append(result)

    output = {
        "produto": subject.get("nome", ""),
        "engine": "visual_media_engine",
        "version": 3,
        "scenes": results,
    }

    with open(folder / "media_search.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=4)

    saved_count = sum(1 for r in results if r["saved"])
    print(f"📸 Visual Media Engine: {saved_count}/{len(results)} cenas com mídia")

    return "visual_engine"
