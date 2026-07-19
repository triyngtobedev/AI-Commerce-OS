"""
Smoke test Hugging Face — gera UMA imagem real via Serverless Inference API.

Uso:
    python -m scripts.video.smoke_test_hf_image
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_PATH = _PROJECT_ROOT / "output" / "smoke_test" / "hf" / "smoke_image.jpg"
_PROMPT = (
    "dramatic documentary photograph, historical atmosphere, photorealistic, "
    "16:9, ancient temple ruins at sunset, cinematic lighting"
)


def main() -> int:
    load_dotenv(_PROJECT_ROOT / ".env")

    from scripts.utils.hf_token import hf_token_configured

    if not hf_token_configured():
        print("ERRO: HF_API_TOKEN ou HF_TOKEN não configurado no .env")
        return 1

    from scripts.video.media_providers.huggingface import HuggingFaceProvider
    from scripts.video.media_providers.huggingface.errors import HFError
    from scripts.video.media_probe import probe_dimensions

    logging.basicConfig(level=logging.INFO)
    print(f"Prompt: {_PROMPT[:80]}...")
    print(f"Saída:  {_OUTPUT_PATH}")
    print("Aguarde — cold start HF pode levar até 30s...\n")

    try:
        provider = HuggingFaceProvider()
        asset = provider.generate_image(_PROMPT, output_path=_OUTPUT_PATH)
    except HFError as error:
        print(f"\nERRO HF [{error.code.value}]: {error}")
        if error.details:
            print(f"Detalhes: {error.details}")
        return 1

    width, height = probe_dimensions(asset.path)
    size_kb = asset.path.stat().st_size // 1024

    print("\n--- Resultado ---")
    print(f"  Arquivo:  {asset.path}")
    print(f"  Modelo:   FLUX.1-schnell via Inference Providers")
    print(f"  Dimensões: {width}x{height}")
    print(f"  MIME:     {asset.mime_type}")
    print(f"  Tamanho:  {size_kb} KB")
    print("\nSMOKE TEST HF IMAGEM: APROVADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
