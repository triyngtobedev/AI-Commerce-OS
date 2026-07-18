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
from scripts.video.scene_timeline import sync_scenes_to_audio
from scripts.youtube.thumbnail_generator import generate_thumbnail
from scripts.audio.soundtrack_engine import generate_soundtrack
from scripts.core.production.quality_score import run_quality_score
from scripts.core.timeline_sync import sync_timeline_to_audio
from scripts.core.emotional_timeline import EmotionalTimeline, build_emotional_timeline
from scripts.core.emotional_effects import apply_effect_hints_to_scenes


def _load_json(path: Path) -> dict | list | None:
    """Carrega JSON ignorando arquivos ausentes, vazios ou corrompidos."""

    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        print(f"⚠️ JSON inválido em {path.name}: {error}")
        return None


def _save_json(path: Path, data: dict | list) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )


def _resolve_emotional_timeline(
    folder: Path,
    script: dict | None,
    audio: Path,
) -> tuple[EmotionalTimeline | None, dict | None]:
    """Carrega ou reconstrói emotional_timeline a partir do roteiro."""

    emotional_file = folder / "emotional_timeline.json"
    emotional_data = _load_json(emotional_file)

    if emotional_data:
        timeline = EmotionalTimeline.from_dict(emotional_data)
    elif script:
        print("♻️ emotional_timeline.json ausente/vazio — reconstruindo a partir do roteiro")
        timeline = build_emotional_timeline(
            script,
            director_meta=script.get("_director"),
        )
        emotional_data = timeline.to_dict()
    else:
        return None, None

    if audio.exists():
        timeline = sync_timeline_to_audio(timeline, str(audio))
        emotional_data = timeline.to_dict()

    _save_json(emotional_file, emotional_data)
    return timeline, emotional_data


def _persist_synced_project(folder: Path, cenas: dict, content: dict) -> None:
    """Atualiza scenes.json e video_project.json com cenas sincronizadas."""

    _save_json(folder / "scenes.json", cenas)

    project_file = folder / "video_project.json"
    project = _load_json(project_file) or {}
    project["cenas"] = cenas
    if content.get("texto_narracao"):
        project["narracao"] = content["texto_narracao"]
    if isinstance(cenas, dict):
        if cenas.get("audio_duration"):
            project["duracao_segundos"] = cenas["audio_duration"]
        project["status"] = "READY_FOR_RENDER"
    _save_json(project_file, project)

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
    scenes_data = _load_json(scenes_file)
    if not scenes_data:
        project_data = _load_json(folder / "video_project.json")
        if isinstance(project_data, dict):
            scenes_data = project_data.get("cenas")

    if not scenes_data:
        print("❌ scenes.json / video_project.json não encontrado ou inválido")
        return None

    result["cenas"] = scenes_data

    audio = folder / "assets" / "audio" / "narracao.mp3"
    if audio.exists():
        result["audio"] = str(audio)

    content = _load_json(folder / "content.json") or {}
    if content:
        result["conteudo"] = content

    strategy = _load_json(folder / "strategy.json") or {}

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
            queries_data = _load_json(queries_file)
            if not queries_data:
                print("❌ asset_queries.json vazio ou inválido — pulando refresh de mídia")
            else:
                if isinstance(queries_data, list):
                    queries = queries_data
                else:
                    queries = queries_data.get("queries", [])

                from scripts.video.visual_media_engine import run_visual_media_pipeline

                print("\n📸 Re-buscando mídia com Visual Media Engine v2...")
                run_visual_media_pipeline(subject, result["cenas"], queries)

    script = _load_json(folder / "script.json")
    emotional_timeline, emotional_data = _resolve_emotional_timeline(
        folder,
        script,
        audio,
    )
    if emotional_data:
        result["emotional_timeline"] = emotional_data

    if audio.exists() and content.get("texto_narracao"):
        result["cenas"] = sync_scenes_to_audio(
            result["cenas"],
            content["texto_narracao"],
            str(audio),
            emotional_timeline=emotional_timeline,
            script=script,
        )
        result["cenas"] = apply_effect_hints_to_scenes(
            result["cenas"],
            emotional_timeline,
        )
        _persist_synced_project(folder, result["cenas"], content)
        synced_count = len(result["cenas"].get("cenas", []))
        print(f"⏱️ Cenas re-sincronizadas: {synced_count} (split de ritmo aplicado)")

    cenas = result.get("cenas", {})
    audio_duration = float(cenas.get("audio_duration", 0)) if isinstance(cenas, dict) else 0
    soundtrack_path = folder / "assets" / "audio" / "soundtrack.mp3"
    soundtrack = generate_soundtrack(
        soundtrack_path,
        emotional_timeline=result.get("emotional_timeline"),
        audio_duration=audio_duration,
        narration_path=audio if audio.exists() else None,
    )
    if soundtrack:
        result["soundtrack"] = str(soundtrack)
        print(f"🎵 Trilha gerada: {soundtrack}")

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

    pr_dict = dict(result)
    pr_dict["youtube_metadata"] = {"thumbnail": str(folder / "thumbnail.jpg")}
    quality = run_quality_score(folder, pr_dict, min_score=70)
    print(f"\n📊 Quality Score: {quality.score}/100 — {'APROVADO' if quality.passed else 'REPROVADO'}")
    if quality.failures:
        for failure in quality.failures:
            print(f"   ❌ {failure}")

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
