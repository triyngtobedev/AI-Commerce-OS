"""
Prepara cópias de imagens para upload no YouTube.

Os arquivos originais em assets/brand/ permanecem intactos.
O YouTube processa JPEG de forma mais confiável que PNG otimizado —
transparência, perfis ICC e compressão PNG podem renderizar como branco.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, Tuple

from scripts.core.brand_profile import BRAND_ASSETS, get_brand

UPLOAD_DIR = BRAND_ASSETS / "upload"
JPEG_QUALITY = 95


def prepare_youtube_upload_image(
    source_path: Path,
    *,
    output_path: Optional[Path] = None,
    background_rgb: Optional[Tuple[int, int, int]] = None,
    max_bytes: Optional[int] = None,
) -> Path:
    """
    Converte imagem para JPEG RGB compatível com YouTube.

    - Achata alpha sobre fundo escuro da marca
    - Remove metadados/ICC
    - Salva JPEG progressivo de alta qualidade

    Retorna caminho do arquivo preparado (temporário ou em output_path).
    """

    from PIL import Image

    source = Path(source_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {source}")

    bg = background_rgb or get_brand().background_color

    with Image.open(source) as img:
        img.load()

        if img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", img.size, bg)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1])
            prepared = background
        elif img.mode == "P":
            prepared = img.convert("RGBA")
            background = Image.new("RGB", prepared.size, bg)
            background.paste(prepared, mask=prepared.split()[-1])
            prepared = background
        elif img.mode != "RGB":
            prepared = img.convert("RGB")
        else:
            prepared = img.copy()

        if output_path:
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
        else:
            suffix = source.stem
            handle = tempfile.NamedTemporaryFile(
                suffix=f"_{suffix}_youtube.jpg",
                delete=False,
            )
            handle.close()
            dest = Path(handle.name)

        quality = JPEG_QUALITY
        prepared.save(
            dest,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=0,
        )

        if max_bytes and dest.stat().st_size > max_bytes:
            for q in (90, 85, 80, 75):
                prepared.save(
                    dest,
                    format="JPEG",
                    quality=q,
                    optimize=True,
                    progressive=True,
                    subsampling=0,
                )
                if dest.stat().st_size <= max_bytes:
                    break

        return dest


def prepare_brand_upload_assets(
    banner_path: Optional[Path] = None,
    profile_path: Optional[Path] = None,
) -> dict[str, Path]:
    """
    Gera cópias prontas para upload em assets/brand/upload/.
    Não altera os PNGs originais.
    """

    banner_src = Path(banner_path or (BRAND_ASSETS / "banner.png"))
    profile_src = Path(profile_path or (BRAND_ASSETS / "profile_picture.png"))

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    banner_upload = prepare_youtube_upload_image(
        banner_src,
        output_path=UPLOAD_DIR / "banner_youtube.jpg",
        max_bytes=6 * 1024 * 1024,
    )
    profile_upload = prepare_youtube_upload_image(
        profile_src,
        output_path=UPLOAD_DIR / "profile_picture_youtube.jpg",
    )

    return {
        "banner_upload": banner_upload,
        "profile_upload": profile_upload,
    }
