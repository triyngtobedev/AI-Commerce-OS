"""
Audio Layer — trilha por mood (3 atos), SFX por regra e ducking sidechain.

Biblioteca fixa em assets/audio/library.json. Sem geração de música por IA.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from scripts.video.media_probe import probe_duration

LIBRARY_PATH = Path("assets/audio/library.json")
AUDIO_ROOT = Path("assets/audio")
RECENT_TRACKS: list[str] = []
MAX_RECENT = 5


def _resolve_track_path(track: dict) -> Path:
    file_ref = track.get("file", "")
    if file_ref.startswith("tracks/"):
        return AUDIO_ROOT / file_ref
    return AUDIO_ROOT / "tracks" / file_ref

_EMOTION_TO_MOOD = {
    "mystery": "investigative",
    "impact": "reveal",
    "calm": "melancholic",
    "warning": "tense",
    "sad": "melancholic",
    "neutral": "investigative",
    "tension": "tense",
    "curiosity": "investigative",
    "revelation": "reveal",
}

_ACT_MOODS = {
    1: "tense",
    2: "investigative",
    3: "reveal",
}

_PROCEDURAL_SPECS = {
    "tense": {"freq": 55, "noise": "brown", "volume": 0.07},
    "investigative": {"freq": 70, "noise": "pink", "volume": 0.06},
    "reveal": {"freq": 85, "noise": "pink", "volume": 0.08},
    "melancholic": {"freq": 90, "noise": "pink", "volume": 0.05},
    "uplifting_end": {"freq": 110, "noise": "pink", "volume": 0.07},
}


def load_library() -> dict:
    if LIBRARY_PATH.exists():
        return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    return {"tracks": [], "sfx": [], "ducking": {}}


def _video_hash(topic: str) -> int:
    return int(hashlib.sha256(topic.encode()).hexdigest()[:8], 16)


def select_track_for_act(
    act: int,
    *,
    topic: str = "",
    emotional_mood: str = "",
) -> dict:
    """Escolhe track por ato + mood, evitando repetição em vídeos consecutivos."""

    library = load_library()
    mood = _ACT_MOODS.get(act, "investigative")
    if emotional_mood:
        mood = _EMOTION_TO_MOOD.get(emotional_mood, mood)

    candidates = [t for t in library.get("tracks", []) if t.get("mood") == mood]
    if not candidates:
        candidates = library.get("tracks", [])

    if not candidates:
        return {"id": "procedural", "mood": mood, "file": f"{mood}_proc.mp3"}

    idx = (_video_hash(topic) + act) % len(candidates)
    for offset in range(len(candidates)):
        pick = candidates[(idx + offset) % len(candidates)]
        if pick["id"] not in RECENT_TRACKS[-MAX_RECENT:]:
            RECENT_TRACKS.append(pick["id"])
            return pick

    return candidates[idx]


def ensure_track_file(track: dict, duration: float, output_dir: Path) -> Path:
    """Garante arquivo de trilha — usa biblioteca local ou gera procedural."""

    output_dir.mkdir(parents=True, exist_ok=True)
    mood = track.get("mood", "investigative")
    library_path = _resolve_track_path(track)
    if library_path.exists() and library_path.stat().st_size > 1000:
        return library_path

    out_path = output_dir / Path(track.get("file", f"{mood}.mp3")).name

    spec = _PROCEDURAL_SPECS.get(mood, _PROCEDURAL_SPECS["investigative"])
    safe_duration = max(30.0, duration + 5.0)
    freq = spec["freq"]
    noise = spec["noise"]

    filter_complex = (
        f"sine=frequency={freq}:sample_rate=44100:duration={safe_duration}[tone];"
        f"anoisesrc=color={noise}:sample_rate=44100:duration={safe_duration},"
        f"lowpass=f=400,volume=0.35[noise];"
        f"[tone][noise]amix=inputs=2:duration=first,volume={spec['volume']},"
        f"afade=t=in:st=0:d=3,afade=t=out:st={safe_duration - 4:.1f}:d=4"
    )

    cmd = [
        "ffmpeg", "-y",
        "-filter_complex", filter_complex,
        "-t", f"{safe_duration:.1f}",
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return out_path if out_path.exists() else out_path


def _generate_sfx_wav(sfx_id: str, dest: Path) -> bool:
    """Gera SFX procedural curto quando arquivo licenciado não existe."""

    specs = {
        "whoosh": "sine=frequency=800:duration=0.4,volume=0.3,afade=t=out:st=0.2:d=0.2",
        "riser": "sine=frequency=200:duration=1.5,volume=0.25,afade=t=in:st=0:d=1.5",
        "impact": "sine=frequency=60:duration=0.3,volume=0.4",
        "sub_drop": "sine=frequency=40:duration=0.6,volume=0.35,afade=t=out:st=0.3:d=0.3",
        "ticking": "sine=frequency=1200:duration=0.1,volume=0.15",
        "ambient_city": "anoisesrc=color=pink:duration=2,volume=0.08,lowpass=f=800",
    }
    filt = specs.get(sfx_id, specs["whoosh"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filt,
        "-c:a", "pcm_s16le",
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return dest.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def resolve_sfx_path(sfx_id: str) -> Optional[Path]:
    library = load_library()
    entry = next((s for s in library.get("sfx", []) if s["id"] == sfx_id), None)
    if not entry:
        return None

    file_ref = entry.get("file", "")
    path = AUDIO_ROOT / file_ref if "/" in file_ref else AUDIO_ROOT / "sfx" / file_ref
    if path.exists():
        return path

    legacy = AUDIO_ROOT / "sfx" / entry.get("file", f"{sfx_id}.wav")
    if legacy.exists():
        return legacy

    if _generate_sfx_wav(sfx_id, legacy):
        return legacy
    return None


def build_sfx_timeline(scenes: dict, *, script: Optional[dict] = None) -> list[dict]:
    """Monta timeline de SFX por regra: whoosh, act_end, reveal."""

    scene_list = scenes.get("cenas", [])
    if not scene_list:
        return []

    act_boundaries = _act_boundaries(len(scene_list))
    events: list[dict] = []

    for index, scene in enumerate(scene_list):
        start = float(scene.get("start_time", scene.get("inicio", 0)) or 0)

        if index > 0:
            events.append({"sfx": "whoosh", "at_s": start, "reason": "scene_change"})

        if index + 1 in act_boundaries:
            events.append({"sfx": "riser", "at_s": start, "reason": "act_end"})
            events.append({"sfx": "impact", "at_s": start + 0.5, "reason": "act_end"})

        if scene.get("tipo") == "revelacao" or scene.get("scene_type") == "climax":
            events.append({"sfx": "sub_drop", "at_s": start, "reason": "reveal"})

    return events


def _act_boundaries(scene_count: int) -> set[int]:
    if scene_count <= 3:
        return {scene_count}
    third = max(1, scene_count // 3)
    return {third, third * 2, scene_count}


def mix_final_audio(
    narration_path: Path,
    output_path: Path,
    *,
    soundtrack_path: Optional[Path] = None,
    sfx_events: Optional[list[dict]] = None,
    duration: float = 0.0,
) -> Optional[Path]:
    """
    Mixa narração + trilha com sidechain ducking + SFX.
    narration 0 dB, música -18 a -22 dB sob narração.
    """

    if not narration_path.exists():
        return None

    if duration <= 0:
        duration = probe_duration(narration_path)
    if duration <= 0:
        duration = 300.0

    library = load_library()
    duck = library.get("ducking", {})
    music_under = float(duck.get("music_under_narration_db", -20))
    music_silence = float(duck.get("music_silence_db", -12))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    has_music = soundtrack_path and soundtrack_path.exists()

    if not has_music and not sfx_events:
        return narration_path

    cmd = ["ffmpeg", "-y", "-i", str(narration_path.resolve())]
    input_idx = 1
    music_idx = None

    if has_music:
        cmd.extend(["-stream_loop", "-1", "-i", str(soundtrack_path.resolve())])
        music_idx = input_idx
        input_idx += 1

    sfx_inputs: list[tuple[int, dict]] = []
    if sfx_events:
        for event in sfx_events[:20]:
            sfx_path = resolve_sfx_path(event.get("sfx", "whoosh"))
            if sfx_path and sfx_path.exists():
                cmd.extend(["-i", str(sfx_path.resolve())])
                sfx_inputs.append((input_idx, event))
                input_idx += 1

    if has_music:
        threshold = 0.02
        ratio = 6
        attack = 0.02
        release = 0.4
        af = (
            f"[{music_idx}:a]volume={music_silence}dB[music_raw];"
            f"[0:a][music_raw]sidechaincompress="
            f"threshold={threshold}:ratio={ratio}:attack={attack}:release={release}:"
            f"makeup=1[ducked];"
            f"[ducked]afade=t=in:st=0:d=2,afade=t=out:st={max(0, duration - 3):.1f}:d=3[music];"
            f"[0:a]volume=0dB[narr];"
        )
        mix_inputs = "[narr][music]"
        if sfx_inputs:
            for idx, (sfx_i, event) in enumerate(sfx_inputs):
                delay_ms = int(float(event.get("at_s", 0)) * 1000)
                label = f"sfx{idx}"
                af += (
                    f"[{sfx_i}:a]adelay={delay_ms}|{delay_ms},"
                    f"volume=-15dB[{label}];"
                )
                mix_inputs += f"[{label}]"
            af += f"{mix_inputs}amix=inputs={2 + len(sfx_inputs)}:duration=first:dropout_transition=2[aout]"
        else:
            af += "[narr][music]amix=inputs=2:duration=first:dropout_transition=2:weights=1.0 0.35[aout]"

        cmd.extend([
            "-filter_complex", af,
            "-map", "[aout]",
            "-t", f"{duration:.3f}",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path),
        ])
    else:
        return narration_path

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        if output_path.exists() and output_path.stat().st_size > 500:
            return output_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    return narration_path


def generate_act_soundtrack(
    output_dir: Path,
    *,
    topic: str,
    emotional_timeline: Any,
    audio_duration: float,
    roteiro_template: str = "",
) -> Optional[Path]:
    """Gera trilha única baseada no mood dominante do ato 2 (corpo do vídeo)."""

    from scripts.audio.soundtrack_engine import _dominant_emotion

    emotion = _dominant_emotion(emotional_timeline)
    track = select_track_for_act(2, topic=topic, emotional_mood=emotion)
    audio_dir = Path(output_dir) / "assets" / "audio"
    path = ensure_track_file(track, audio_duration, audio_dir / "library_cache")
    if path.exists():
        dest = audio_dir / "soundtrack.mp3"
        if path != dest:
            dest.write_bytes(path.read_bytes())
        return dest
    return None
