"""Simple Wikimedia Commons footage downloader — bypasses visual_media_engine."""

import subprocess

import requests


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

        # 2. Search Wikimedia Commons
        url = f"https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "6",
            "srlimit": "3",
            "format": "json",
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            hits = data.get("query", {}).get("search", [])

            image_url = None
            for hit in hits:
                title = hit.get("title", "")
                if any(title.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                    # Get direct image URL
                    title_encoded = title.replace(" ", "_")
                    info_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={title_encoded}&prop=imageinfo&iiprop=url&format=json"
                    info = requests.get(info_url, timeout=10).json()
                    pages = info.get("query", {}).get("pages", {})
                    for page in pages.values():
                        imageinfo = page.get("imageinfo", [])
                        if imageinfo:
                            image_url = imageinfo[0].get("url")
                            break
                if image_url:
                    break

            if not image_url:
                # fallback: use a solid color frame
                img_path = f"{output_dir}/scene_{i}_color.jpg"
                subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    f"color=c=0x1a1a2e:size=1920x1080:rate=1", "-frames:v", "1",
                    img_path], capture_output=True)
            else:
                # Download image
                img_path = f"{output_dir}/scene_{i}.jpg"
                img_data = requests.get(image_url, timeout=30).content
                with open(img_path, "wb") as f:
                    f.write(img_data)

            # 3. Convert to Ken Burns MP4
            mp4_path = f"{output_dir}/scene_{i}.mp4"
            subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img_path,
                "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0008,1.2)':d=150:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',fps=25",
                "-t", "60", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                mp4_path], capture_output=True)

            results.append(mp4_path)
            print(f"✅ Cena {i+1}: {mp4_path}")

        except Exception as e:
            print(f"⚠️ Cena {i+1} falhou: {e} — usando cor sólida")
            mp4_path = f"{output_dir}/scene_{i}_fallback.mp4"
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                "-i", "color=c=0x1a1a2e:size=1920x1080:rate=25",
                "-t", "60", "-c:v", "libx264", mp4_path], capture_output=True)
            results.append(mp4_path)

    return results
