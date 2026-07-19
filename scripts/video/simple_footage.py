"""Simple Wikimedia Commons footage downloader — bypasses visual_media_engine."""

import subprocess
import time

import requests

WIKIMEDIA_MAX_RETRIES = 3
WIKIMEDIA_RETRY_DELAY = 2
GRADIENT_FILTER = "gradients=s=1920x1080:c0=0x0a0a1a:c1=0x1a1a3e"


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


def _resolve_image_url(query: str) -> str | None:
    """Try full query, then a single-word fallback."""
    image_url = _search_wikimedia_image(query)
    if image_url:
        return image_url

    words = query.strip().split()
    if len(words) > 1:
        fallback = words[0]
        print(f"[Wikimedia] Trying 1-word fallback query: {fallback!r}")
        return _search_wikimedia_image(fallback)
    return None


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
            image_url = _resolve_image_url(query)

            if not image_url:
                img_path = f"{output_dir}/scene_{i}_gradient.jpg"
                print(f"⚠️ Cena {i + 1}: Wikimedia vazio — usando gradiente escuro")
                _create_gradient_frame(img_path)
            else:
                img_path = f"{output_dir}/scene_{i}.jpg"
                img_data = requests.get(image_url, timeout=30).content
                with open(img_path, "wb") as f:
                    f.write(img_data)

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
