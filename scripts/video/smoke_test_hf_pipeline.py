"""
Smoke test do pipeline visual_media_engine — força fallback HF.

Pollinations é mockado para falhar; valida que _try_ai_image cai no HF
e retorna provedor "huggingface" com imagem válida (incluindo upscale).

Uso:
    python -m scripts.video.smoke_test_hf_pipeline
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_DIR = _PROJECT_ROOT / "output" / "smoke_test" / "hf" / "pipeline"
_PROMPT = "ancient temple ruins documentary cinematic scene"


def main() -> int:
    load_dotenv(_PROJECT_ROOT / ".env")

    from scripts.video.media_providers.huggingface.adapter import hf_is_configured
    from scripts.video.media_probe import probe_dimensions
    from scripts.video.visual_media_engine import _try_ai_image

    if not hf_is_configured():
        print("ERRO: HF_TOKEN não configurado no .env")
        return 1

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scene_image = _OUTPUT_DIR / "scene-hf-fallback.jpg"

    if scene_image.exists():
        scene_image.unlink()

    print("Forçando Pollinations a falhar — testando fallback HF no pipeline...")
    print(f"Prompt: {_PROMPT}")
    print(f"Saída:  {scene_image}\n")

    with patch(
        "scripts.video.visual_media_engine.generate_pollinations_image",
        return_value=False,
    ):
        saved, provider = _try_ai_image(_PROMPT, scene_image, allow_upscale=True)

    if not saved:
        print("FALHOU: _try_ai_image retornou False")
        return 1

    if provider != "huggingface":
        print(f"FALHOU: provedor esperado 'huggingface', obtido '{provider}'")
        return 1

    if not scene_image.exists():
        print(f"FALHOU: arquivo não encontrado em {scene_image}")
        return 1

    width, height = probe_dimensions(scene_image)
    size_kb = scene_image.stat().st_size // 1024

    print("--- Resultado ---")
    print(f"  Provedor:   {provider}")
    print(f"  Arquivo:    {scene_image}")
    print(f"  Dimensões:  {width}x{height}")
    print(f"  Tamanho:    {size_kb} KB")

    if width < 1920 or height < 1080:
        print(f"\nAVISO: upscale esperado 1920x1080, obtido {width}x{height}")
        print("(ffmpeg pode não estar no PATH — imagem HF ainda foi gerada)")

    print("\nSMOKE TEST PIPELINE HF FALLBACK: APROVADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
