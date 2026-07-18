"""
Upscale pós-geração de vídeo — Real-ESRGAN frame-by-frame ou fallback FFmpeg.

480p → 960p com scale=2 (Wan2.2 / LTX free tier).

Requer:
    - ffmpeg no PATH (obrigatório para remux)
    - realesrgan-ncnn-vulkan no PATH (opcional, melhor qualidade)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("video_upscaler")


def _which(name: str) -> str | None:
    return shutil.which(name)


def ffmpeg_available() -> bool:
    """True se ffmpeg está no PATH."""
    return _which("ffmpeg") is not None


def realesrgan_available() -> bool:
    """True se realesrgan-ncnn-vulkan está no PATH."""
    return _which("realesrgan-ncnn-vulkan") is not None


def upscale_video_ffmpeg(input_path: str, scale: int = 2) -> str:
    """
    Upscale simples via ffmpeg bicubic.

    800x512 → 1600x1024 com scale=2.
    Não exige GPU — roda em CPU.

    Args:
        input_path: Caminho do MP4 de entrada.
        scale: Fator de upscale (default 2).

    Returns:
        Caminho do vídeo upscalado (substitui sufixo _upscaled ou cria novo).

    Raises:
        FileNotFoundError: Se input_path não existir.
        RuntimeError: Se ffmpeg não estiver disponível ou upscale falhar.
    """
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Vídeo não encontrado: {source}")

    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg não encontrado no PATH. Instale FFmpeg antes de fazer upscale."
        )

    output_path = source.with_name(f"{source.stem}_upscaled{source.suffix}")
    ffmpeg = _which("ffmpeg")
    assert ffmpeg

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vf",
        f"scale=iw*{scale}:ih*{scale}:flags=bicubic",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-c:a",
        "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    if not output_path.exists() or output_path.stat().st_size < 5000:
        raise RuntimeError("Upscale FFmpeg produziu arquivo inválido.")

    return str(output_path)


def upscale_video(input_path: str, scale: int = 2) -> str:
    """
    Aplica Real-ESRGAN frame-by-frame no vídeo.
    480p → 960p com scale=2.

    Usa ffmpeg + realesrgan-ncnn-vulkan quando disponível;
    caso contrário, upscale via filtro scale do ffmpeg.

    Args:
        input_path: Caminho do MP4 de entrada.
        scale: Fator de upscale (2 = dobro da resolução).

    Returns:
        Caminho do vídeo upscalado.

    Raises:
        FileNotFoundError: Se input_path não existir.
        RuntimeError: Se ffmpeg não estiver disponível ou upscale falhar.
    """
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Vídeo não encontrado: {source}")

    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg não encontrado no PATH. Instale FFmpeg antes de fazer upscale."
        )

    output_path = source.with_name(f"{source.stem}_upscaled{source.suffix}")

    if realesrgan_available():
        return _upscale_with_realesrgan(source, output_path, scale)

    logger.warning("realesrgan-ncnn-vulkan não encontrado — usando upscale FFmpeg (bicubic).")
    return upscale_video_ffmpeg(str(source), scale=scale)


def _upscale_with_realesrgan(source: Path, output_path: Path, scale: int) -> str:
    """Extrai frames, upscale com Real-ESRGAN e remuxa com ffmpeg."""
    realesrgan = _which("realesrgan-ncnn-vulkan")
    ffmpeg = _which("ffmpeg")
    assert realesrgan and ffmpeg

    with tempfile.TemporaryDirectory(prefix="video_upscale_") as tmp:
        tmp_dir = Path(tmp)
        frames_in = tmp_dir / "frames_in"
        frames_out = tmp_dir / "frames_out"
        frames_in.mkdir()
        frames_out.mkdir()

        extract_cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-qscale:v",
            "2",
            str(frames_in / "frame_%06d.png"),
        ]
        subprocess.run(extract_cmd, check=True, capture_output=True)

        frame_files = sorted(frames_in.glob("frame_*.png"))
        if not frame_files:
            raise RuntimeError("Nenhum frame extraído para upscale.")

        for frame in frame_files:
            out_frame = frames_out / frame.name
            upscale_cmd = [
                realesrgan,
                "-i",
                str(frame),
                "-o",
                str(out_frame),
                "-s",
                str(scale),
                "-n",
                "realesrgan-x4plus",
            ]
            subprocess.run(upscale_cmd, check=True, capture_output=True)

        remux_cmd = [
            ffmpeg,
            "-y",
            "-framerate",
            "24",
            "-i",
            str(frames_out / "frame_%06d.png"),
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "copy",
            "-shortest",
            str(output_path),
        ]
        subprocess.run(remux_cmd, check=True, capture_output=True)

    if not output_path.exists() or output_path.stat().st_size < 5000:
        raise RuntimeError("Upscale Real-ESRGAN produziu arquivo inválido.")

    return str(output_path)


def _upscale_with_ffmpeg(source: Path, output_path: Path, scale: int) -> str:
    """Fallback: upscale via filtro scale do ffmpeg."""
    ffmpeg = _which("ffmpeg")
    assert ffmpeg

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vf",
        f"scale=iw*{scale}:ih*{scale}:flags=lanczos",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    if not output_path.exists() or output_path.stat().st_size < 5000:
        raise RuntimeError("Upscale FFmpeg produziu arquivo inválido.")

    return str(output_path)
