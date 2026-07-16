"""
Re-render de vídeo YouTube Dark com engines atualizados.

Uso:
  python -m scripts.youtube.rerender_test output/youtube_dark/o-misterio-da-explosao-de-tunguska
  python -m scripts.youtube.rerender_test output/youtube_dark/o-misterio-da-explosao-de-tunguska --refresh-media
  python -m scripts.youtube.rerender_test output/youtube_dark/o-misterio-da-explosao-de-tunguska --thumbnail
"""

import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.video.subtitle_generator import generate_subtitles
from scripts.video.renderer import render_video_project
from scripts.youtube.thumbnail_generator import generate_thumbnail


def rerender(
    folder_path: str,
    refresh_media: bool = False,
    regenerate_thumbnail: bool = True,
) -> Path | None:
    folder = Path(folder_path)

    if not folder.exists():
        print(f"❌ Pasta não encontrada: {folder}")
        return None

    subject = {
        "nome": folder.name.replace("-", " ").title(),
        "_output_platform": "youtube_dark",
    }

    result = {
        "produto": subject,
        "platform": "youtube_dark",
    }

    scenes_file = folder / "scenes.json"
    if scenes_file.exists():
        with open(scenes_file, encoding="utf-8") as f:
            result["cenas"] = json.load(f)
    else:
        print("❌ scenes.json não encontrado")
        return None

    audio = folder / "assets" / "audio" / "narracao.mp3"
    if audio.exists():
        result["audio"] = str(audio)

    content = {}
    content_file = folder / "content.json"
    if content_file.exists():
        with open(content_file, encoding="utf-8") as f:
            content = json.load(f)
            result["conteudo"] = content

    strategy = {}
    strategy_file = folder / "strategy.json"
    if strategy_file.exists():
        with open(strategy_file, encoding="utf-8") as f:
            strategy = json.load(f)

    previous_video = folder / "video_final.mp4"
    backup_path = folder / "video_final_previous.mp4"
    if previous_video.exists():
        shutil.copy2(previous_video, backup_path)
        print(f"📦 Backup do vídeo anterior: {backup_path}")

    if refresh_media:
        queries_file = folder / "asset_queries.json"
        if not queries_file.exists():
            print("❌ asset_queries.json não encontrado — pulando refresh de mídia")
        else:
            with open(queries_file, encoding="utf-8") as f:
                queries_data = json.load(f)
            if isinstance(queries_data, list):
                queries = queries_data
            else:
                queries = queries_data.get("queries", [])

            from scripts.video.visual_media_engine import run_visual_media_pipeline

            print("\n📸 Re-buscando mídia com Visual Media Engine v2...")
            run_visual_media_pipeline(subject, result["cenas"], queries)

    subtitle = generate_subtitles(result)
    result["subtitle_file"] = str(subtitle)

    print("\n🎬 Re-renderizando com BrandKit + estilo cinematográfico...")
    video = render_video_project(result)

    if video:
        print(f"\n✅ Vídeo re-renderizado: {video}")
    else:
        print("\n❌ Falha no re-render")
        return None

    if regenerate_thumbnail:
        print("\n🖼️ Regenerando thumbnail com BrandKit...")
        old_thumb = folder / "thumbnail.jpg"
        if old_thumb.exists():
            shutil.copy2(old_thumb, folder / "thumbnail_previous.jpg")

        thumbnail = generate_thumbnail(
            subject,
            content,
            video_path=str(video),
            platform="youtube_dark",
            scenes=result.get("cenas"),
            strategy=strategy,
        )
        if thumbnail:
            print(f"✅ Thumbnail: {thumbnail}")

    return video


if __name__ == "__main__":
    args = sys.argv[1:]
    refresh = "--refresh-media" in args
    no_thumb = "--no-thumbnail" in args
    args = [a for a in args if a not in ("--refresh-media", "--no-thumbnail")]

    path = args[0] if args else (
        "output/youtube_dark/o-misterio-da-explosao-de-tunguska"
    )
    rerender(path, refresh_media=refresh, regenerate_thumbnail=not no_thumb)
