"""
Smoke test do pipeline YouTube Dark — valida sync, legendas e thumbnail local.

Uso:
  python -m scripts.youtube.smoke_test_youtube
  python -m scripts.youtube.smoke_test_youtube output/youtube_dark/<slug>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.video.scene_timeline import split_long_scenes, sync_scenes_to_audio
from scripts.video.subtitle_generator import generate_subtitles
from scripts.video.subtitle_engine import validate_srt_timing
from scripts.youtube.thumbnail_generator import generate_thumbnail
from scripts.core.brand_engine import get_render_style


def _load_project(folder: Path) -> dict | None:
    vp = folder / "video_project.json"
    if vp.exists():
        return json.loads(vp.read_text(encoding="utf-8"))

    scenes_file = folder / "scenes.json"
    if scenes_file.exists():
        return {"cenas": json.loads(scenes_file.read_text(encoding="utf-8"))}

    return None


def run_smoke(folder_path: str) -> int:
    folder = Path(folder_path)
    if not folder.exists():
        print(f"FAIL: pasta não encontrada: {folder}")
        return 1

    project = _load_project(folder)
    if not project:
        print("FAIL: video_project.json ou scenes.json ausente")
        return 1

    cenas = project.get("cenas", {})
    scenes = cenas.get("cenas", []) if isinstance(cenas, dict) else cenas
    audio = folder / "assets" / "audio" / "narracao.mp3"

    print(f"Smoke test: {folder.name}")
    print(f"  Cenas originais: {len(scenes)}")

    failures = []

    # 1. Ritmo — nenhuma cena acima de 20s após split
    split_result = split_long_scenes(cenas if isinstance(cenas, dict) else {"cenas": scenes})
    split_scenes = split_result["cenas"]
    long_scenes = [
        s for s in split_scenes if float(s.get("duration_seconds", 0)) > 20.0
    ]
    print(f"  Cenas após split: {len(split_scenes)} (longas>{20}s: {len(long_scenes)})")
    if long_scenes:
        failures.append(f"ritmo: {len(long_scenes)} cenas acima de 20s")

    # 2. Re-sync se áudio disponível
    if audio.exists():
        content_file = folder / "content.json"
        narracao = ""
        if content_file.exists():
            content = json.loads(content_file.read_text(encoding="utf-8"))
            narracao = content.get("texto_narracao", "")

        synced = sync_scenes_to_audio(
            cenas if isinstance(cenas, dict) else {"cenas": scenes},
            narracao,
            str(audio),
        )
        synced_long = [
            s for s in synced["cenas"]
            if float(s.get("duration_seconds", 0)) > 20.0
        ]
        print(f"  Re-sync com áudio: {len(synced['cenas'])} cenas, longas>{20}s: {len(synced_long)}")
        if synced_long:
            failures.append(f"sync: {len(synced_long)} cenas acima de 20s após re-sync")
        split_result = synced

    # 3. Legendas
    subject = {"nome": folder.name, "_output_platform": "youtube_dark"}
    subtitle_path = generate_subtitles({"produto": subject, "cenas": split_result})
    srt = subtitle_path.read_text(encoding="utf-8")
    audio_dur = float(split_result.get("audio_duration", project.get("duracao_segundos", 0)))
    offset = get_render_style("youtube_dark").intro_seconds
    ok, reason = validate_srt_timing(srt, audio_dur, timing_offset=offset)
    print(f"  Legendas: {subtitle_path.name} — validação: {reason}")
    if not ok and audio_dur > 0:
        failures.append(f"legendas: {reason}")

    # 4. Thumbnail local
    content = {}
    content_file = folder / "content.json"
    if content_file.exists():
        content = json.loads(content_file.read_text(encoding="utf-8"))
    strategy = {}
    strategy_file = folder / "strategy.json"
    if strategy_file.exists():
        strategy = json.loads(strategy_file.read_text(encoding="utf-8"))

    thumb = generate_thumbnail(
        subject,
        content,
        platform="youtube_dark",
        scenes=split_result,
        strategy=strategy,
    )
    thumb_path = folder / "thumbnail.jpg"
    if thumb and thumb_path.exists() and thumb_path.stat().st_size > 2048:
        print(f"  Thumbnail: OK ({thumb_path.stat().st_size // 1024} KB)")
    else:
        failures.append("thumbnail: não gerada ou arquivo inválido")

    if failures:
        print("\nSMOKE TEST: REPROVADO")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nSMOKE TEST: APROVADO")
    return 0


if __name__ == "__main__":
    default = (
        "output/youtube_dark/"
        "o-templo-mais-antigo-do-mundo-a-descoberta-que-reescreveu-a-historia-da-civilizacao-humana"
    )
    path = sys.argv[1] if len(sys.argv) > 1 else default
    raise SystemExit(run_smoke(path))
