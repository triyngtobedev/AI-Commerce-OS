"""
Popula assets/audio/ com tracks e SFX reais para a biblioteca Sprint 30.

Gera arquivos locais via FFmpeg (documentary ambient beds) quando downloads
externos não estão disponíveis. Idempotente — pula arquivos existentes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

LIBRARY_PATH = Path("assets/audio/library.json")
TRACKS_DIR = Path("assets/audio/tracks")
SFX_DIR = Path("assets/audio/sfx")

_TRACK_SPECS = {
    "tense_01.mp3": {"mood": "tense", "freq": 52, "noise": "brown", "vol": 0.07, "bpm": 72},
    "tense_02.mp3": {"mood": "tense", "freq": 58, "noise": "brown", "vol": 0.065, "bpm": 68},
    "investigative_01.mp3": {"mood": "investigative", "freq": 68, "noise": "pink", "vol": 0.06, "bpm": 80},
    "investigative_02.mp3": {"mood": "investigative", "freq": 74, "noise": "pink", "vol": 0.055, "bpm": 76},
    "reveal_01.mp3": {"mood": "reveal", "freq": 82, "noise": "pink", "vol": 0.08, "bpm": 90},
    "reveal_02.mp3": {"mood": "reveal", "freq": 88, "noise": "pink", "vol": 0.075, "bpm": 88},
    "melancholic_01.mp3": {"mood": "melancholic", "freq": 92, "noise": "pink", "vol": 0.05, "bpm": 60},
    "melancholic_02.mp3": {"mood": "melancholic", "freq": 96, "noise": "pink", "vol": 0.048, "bpm": 58},
    "uplifting_end_01.mp3": {"mood": "uplifting_end", "freq": 108, "noise": "pink", "vol": 0.07, "bpm": 96},
    "uplifting_end_02.mp3": {"mood": "uplifting_end", "freq": 112, "noise": "pink", "vol": 0.068, "bpm": 94},
}

_SFX_SPECS = {
    "whoosh.wav": "sine=frequency=900:duration=0.35,volume=0.28,afade=t=out:st=0.15:d=0.2",
    "riser.wav": "sine=frequency=180:duration=1.4,volume=0.22,afade=t=in:st=0:d=1.4",
    "impact.wav": "sine=frequency=55:duration=0.25,volume=0.38",
    "sub_drop.wav": "sine=frequency=38:duration=0.55,volume=0.32,afade=t=out:st=0.25:d=0.3",
    "ticking.wav": "sine=frequency=1400:duration=0.08,volume=0.14",
    "ambient_city.wav": "anoisesrc=color=pink:duration=3,volume=0.07,lowpass=f=700,highpass=f=120",
}


def _generate_track(path: Path, spec: dict, duration: float = 120.0) -> bool:
    if path.exists() and path.stat().st_size > 5000:
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    freq = spec["freq"]
    noise = spec["noise"]
    vol = spec["vol"]
    filt = (
        f"sine=frequency={freq}:sample_rate=44100:duration={duration}[tone];"
        f"anoisesrc=color={noise}:sample_rate=44100:duration={duration},"
        f"lowpass=f=450,volume=0.35[noise];"
        f"[tone][noise]amix=inputs=2:duration=first,volume={vol},"
        f"afade=t=in:st=0:d=4,afade=t=out:st={duration - 5:.1f}:d=5"
    )
    cmd = [
        "ffmpeg", "-y", "-filter_complex", filt,
        "-t", f"{duration:.1f}",
        "-c:a", "libmp3lame", "-b:a", "160k",
        str(path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        return path.exists() and path.stat().st_size > 5000
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _generate_sfx(path: Path, filt: str) -> bool:
    if path.exists() and path.stat().st_size > 500:
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", filt, "-c:a", "pcm_s16le", str(path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return path.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def populate_audio_library(*, track_duration: float = 180.0) -> dict:
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    tracks = []
    for filename, spec in _TRACK_SPECS.items():
        path = TRACKS_DIR / filename
        ok = _generate_track(path, spec, duration=track_duration)
        tracks.append({
            "id": filename.replace(".mp3", ""),
            "mood": spec["mood"],
            "file": f"tracks/{filename}",
            "source": "local_library",
            "license": "royalty_free_generated",
            "bpm": spec["bpm"],
            "duration_s": track_duration,
            "ready": ok,
        })

    sfx = []
    for filename, filt in _SFX_SPECS.items():
        path = SFX_DIR / filename
        ok = _generate_sfx(path, filt)
        sfx_id = filename.replace(".wav", "")
        sfx.append({
            "id": sfx_id,
            "file": f"sfx/{filename}",
            "volume_db": -15,
            "trigger": {
                "whoosh": "scene_change",
                "riser": "act_end",
                "impact": "act_end",
                "sub_drop": "reveal",
                "ticking": "tension",
                "ambient_city": "ambient",
            }.get(sfx_id, "scene_change"),
            "ready": ok,
        })

    library = {
        "version": 2,
        "tracks": tracks,
        "sfx": sfx,
        "ducking": {
            "narration_db": 0,
            "music_under_narration_db": -20,
            "music_silence_db": -12,
            "sfx_db": -15,
        },
    }

    LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY_PATH.write_text(json.dumps(library, ensure_ascii=False, indent=2), encoding="utf-8")

    ready_tracks = sum(1 for t in tracks if t["ready"])
    ready_sfx = sum(1 for s in sfx if s["ready"])
    print(f"🎵 Biblioteca populada: {ready_tracks}/{len(tracks)} tracks, {ready_sfx}/{len(sfx)} SFX")
    print(f"   → {LIBRARY_PATH}")

    return library


if __name__ == "__main__":
    populate_audio_library()
