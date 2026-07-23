"""Simple Wikimedia Commons footage downloader — bypasses visual_media_engine."""

import os
import subprocess
import time

import requests

WIKIMEDIA_MAX_RETRIES = 3
WIKIMEDIA_RETRY_DELAY = 2
GRADIENT_FILTER = "gradients=s=1920x1080:c0=0x0a0a1a:c1=0x1a1a3e"

# Termos de estilo cinematográfico — queries chegam em inglês via Groq
_STYLE_NOISE = frozenset({
    "dark", "documentary", "cinematic", "reveal", "dramatic", "mystery",
    "conspiracy", "investigation", "footage", "close", "up", "closeup",
    "unexplained", "truth", "discovery", "forensic", "evidence", "secret",
    "shocking", "revealed", "exclusive", "inside", "story", "real",
    "unknown", "bizarre", "strange", "weird",
    "incredible", "amazing", "ultimate", "complete", "full", "hidden",
})


def _simplify_for_stock(query: str) -> str:
    """Remove ruído cinematográfico de queries em inglês, mantém contexto histórico."""
    words = query.strip().split()
    if not words:
        return query
    filtered = [w for w in words if w.lower().strip(".,!?;:") not in _STYLE_NOISE]
    if not filtered:
        filtered = words[:3]
    simplified = " ".join(filtered[:4]).strip()
    return simplified if len(simplified) > 3 else " ".join(words[:3])


def _wikimedia_get_json(url: str, params: dict | None = None) -> dict:
    """GET Wikimedia API with retries; raises on empty or invalid JSON."""
    last_error = None
    for attempt in range(WIKIMEDIA_MAX_RETRIES):
        try:
            r = requests.get(url, params=params, timeout=10)
            if not r.text.strip():
                raise ValueError("Empty response from Wikimedia")
            return r.json()
        except Exception as exc:
            last_error = exc
            if attempt < WIKIMEDIA_MAX_RETRIES - 1:
                print(
                    f"[Wikimedia] Attempt {attempt + 1}/{WIKIMEDIA_MAX_RETRIES} failed: {exc} — retrying..."
                )
                time.sleep(WIKIMEDIA_RETRY_DELAY)
    raise last_error  # type: ignore[misc]


def _search_wikimedia_image(query: str) -> str | None:
    """Search Wikimedia Commons and return a direct image URL, or None."""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": "3",
        "format": "json",
    }
    try:
        data = _wikimedia_get_json(url, params)
    except Exception as exc:
        print(f"[Wikimedia] Search failed for {query!r}: {exc}")
        return None

    hits = data.get("query", {}).get("search", [])
    for hit in hits:
        title = hit.get("title", "")
        if not any(title.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
            continue
        title_encoded = title.replace(" ", "_")
        info_url = "https://commons.wikimedia.org/w/api.php"
        info_params = {
            "action": "query",
            "titles": title_encoded,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
        try:
            info = _wikimedia_get_json(info_url, info_params)
        except Exception as exc:
            print(f"[Wikimedia] imageinfo failed for {title!r}: {exc}")
            continue
        pages = info.get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                return imageinfo[0].get("url")
    return None


def _download_image(url: str, dest: str) -> bool:
    try:
        data = requests.get(url, timeout=30).content
        if not data:
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as exc:
        print(f"[Footage] Download failed ({url!r}): {exc}")
        return False


def _search_pixabay_image(query: str) -> str | None:
    """Search Pixabay for a photo URL, or return None."""
    api_key = os.getenv("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": api_key, "q": query, "per_page": 5,
                "safesearch": "true", "orientation": "horizontal",
                "image_type": "photo", "min_width": 1920,
            },
            timeout=10,
        )
        hits = r.json().get("hits", [])
        if hits:
            url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
            if url:
                print(f"[Pixabay] Foto encontrada para {query!r}")
                return url
    except Exception as exc:
        print(f"[Pixabay] Falha na busca ({query!r}): {exc}")
    return None


def _search_pexels_image(query: str) -> str | None:
    """Search Pexels for a photo URL, or return None."""
    api_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 5, "orientation": "landscape"},
            timeout=10,
        )
        photos = r.json().get("photos", [])
        if photos:
            src = photos[0].get("src", {})
            url = src.get("original") or src.get("large") or src.get("medium")
            if url:
                print(f"[Pexels] Foto encontrada para {query!r}")
                return url
    except Exception as exc:
        print(f"[Pexels] Falha na busca ({query!r}): {exc}")
    return None


def _resolve_image_url(query: str, scene_index: int = 0) -> str | None:
    """Try Wikimedia, Pixabay, Pexels, then Lorem Picsum."""
    # 1. Wikimedia (query completa)
    image_url = _search_wikimedia_image(query)
    if image_url:
        return image_url

    # 2. Wikimedia (2 primeiras palavras)
    words = query.strip().split()
    if len(words) > 2:
        short_query = " ".join(words[:2])
        print(f"[Wikimedia] Trying 2-word fallback query: {short_query!r}")
        image_url = _search_wikimedia_image(short_query)
        if image_url:
            return image_url

    # 3. Pixabay (query simplificada para stock)
    stock_query = _simplify_for_stock(query)
    if stock_query != query:
        print(f"[Footage] Pixabay query simplificada: {query!r} -> {stock_query!r}")
    image_url = _search_pixabay_image(stock_query)
    if image_url:
        return image_url

    # 4. Pexels (query simplificada para stock)
    image_url = _search_pexels_image(stock_query)
    if image_url:
        return image_url

    # 5. Fallback: Lorem Picsum
    picsum_url = f"https://picsum.photos/1920/1080?random={scene_index}"
    print(f"[Footage] Using Lorem Picsum fallback: {picsum_url}")
    return picsum_url


def _create_gradient_frame(output_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", GRADIENT_FILTER, "-frames:v", "1", output_path],
        capture_output=True,
    )


def _create_gradient_mp4(output_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", GRADIENT_FILTER,
            "-t", "60", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path,
        ],
        capture_output=True,
    )


def get_footage_for_scenes(scenes: list, output_dir: str) -> list:
    """
    For each scene, download one image from Wikimedia Commons.
    Convert it to a 60-second Ken Burns MP4.
    Returns list of MP4 file paths, one per scene.
    """
    results = []
    for i, scene in enumerate(scenes):
        # 1. Get visual query - handle both dict and any other type safely
        if isinstance(scene, dict):
            query = scene.get("visual") or scene.get("visual_query") or scene.get("tipo", "mystery")
        else:
            query = "ancient mystery documentary"

        try:
            image_url = _resolve_image_url(query, scene_index=i)

            if not image_url:
                img_path = f"{output_dir}/scene_{i}_gradient.jpg"
                print(f"⚠️ Cena {i + 1}: sem imagem — usando gradiente escuro")
                _create_gradient_frame(img_path)
            else:
                img_path = f"{output_dir}/scene_{i}.jpg"
                if not _download_image(image_url, img_path):
                    img_path = f"{output_dir}/scene_{i}_gradient.jpg"
                    print(f"⚠️ Cena {i + 1}: download falhou — usando gradiente escuro")
                    _create_gradient_frame(img_path)

            # 3. Convert to Ken Burns MP4
            mp4_path = f"{output_dir}/scene_{i}.mp4"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loop", "1", "-i", img_path,
                    "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
                    "zoompan=z='min(zoom+0.0008,1.2)':d=150:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',fps=25",
                    "-t", "60", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    mp4_path,
                ],
                capture_output=True,
            )

            results.append(mp4_path)
            print(f"✅ Cena {i + 1}: {mp4_path}")

        except Exception as e:
            print(f"⚠️ Cena {i + 1} falhou: {e} — usando gradiente escuro")
            mp4_path = f"{output_dir}/scene_{i}_fallback.mp4"
            _create_gradient_mp4(mp4_path)
            results.append(mp4_path)

    return results
