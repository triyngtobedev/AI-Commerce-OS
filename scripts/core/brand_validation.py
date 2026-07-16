"""
Validação centralizada de assets de marca.

Todo asset deve passar por validate_brand_asset() antes do upload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

BANNER_MIN_WIDTH = 2048
BANNER_MIN_HEIGHT = 1152
BANNER_MAX_BYTES = 6 * 1024 * 1024

PROFILE_MIN_SIZE = 1

ASSET_RULES = {
    "banner": {
        "min_width": BANNER_MIN_WIDTH,
        "min_height": BANNER_MIN_HEIGHT,
        "max_bytes": BANNER_MAX_BYTES,
    },
    "profile": {
        "min_width": PROFILE_MIN_SIZE,
        "min_height": PROFILE_MIN_SIZE,
        "max_bytes": None,
    },
    "thumbnail": {
        "min_width": 640,
        "min_height": 360,
        "max_bytes": 2 * 1024 * 1024,
    },
    "image": {
        "min_width": 1,
        "min_height": 1,
        "max_bytes": None,
    },
}


@dataclass
class BrandAssetReport:
    path: Path
    asset_type: str
    exists: bool
    valid: bool
    absolute_path: str = ""
    file_name: str = ""
    size_bytes: int = 0
    width: int = 0
    height: int = 0
    format: str = ""
    color_mode: str = ""
    unique_colors_sampled: int = 0
    is_blank: bool = False
    messages: List[str] = field(default_factory=list)

    def log_lines(self) -> List[str]:
        lines = [
            f"  arquivo: {self.file_name}",
            f"  caminho absoluto: {self.absolute_path}",
            f"  tamanho: {self.size_bytes} bytes",
            f"  dimensões: {self.width}x{self.height}",
            f"  formato: {self.format or 'desconhecido'}",
            f"  modo de cor: {self.color_mode or 'desconhecido'}",
            f"  cores distintas (amostra): {self.unique_colors_sampled}",
            f"  pixels válidos: {'sim' if self.valid and not self.is_blank else 'não'}",
        ]
        lines.extend(f"  ⚠️ {message}" for message in self.messages)
        return lines


def validate_brand_asset(
    image_path: Path,
    asset_type: str = "image",
    *,
    min_width: Optional[int] = None,
    min_height: Optional[int] = None,
    max_bytes: Optional[int] = None,
    label: Optional[str] = None,
) -> BrandAssetReport:
    """
    Valida arquivo de imagem de marca antes do upload.

    asset_type: banner | profile | thumbnail | image
    """

    rules = ASSET_RULES.get(asset_type, ASSET_RULES["image"])
    resolved = Path(image_path).resolve()
    display_label = label or asset_type

    report = BrandAssetReport(
        path=image_path,
        asset_type=asset_type,
        exists=resolved.exists(),
        valid=False,
        absolute_path=str(resolved),
        file_name=resolved.name,
    )

    if not report.exists:
        report.messages.append(f"{display_label} não encontrada: {resolved}")
        return report

    report.size_bytes = resolved.stat().st_size

    if report.size_bytes == 0:
        report.messages.append("arquivo vazio (0 bytes)")
        return report

    effective_max = max_bytes if max_bytes is not None else rules.get("max_bytes")
    if effective_max and report.size_bytes > effective_max:
        report.messages.append(
            f"tamanho {report.size_bytes} bytes excede o limite de {effective_max} bytes"
        )
        return report

    try:
        from PIL import Image
    except ImportError as error:
        report.messages.append(f"Pillow não instalado: {error}")
        return report

    effective_min_w = min_width if min_width is not None else rules["min_width"]
    effective_min_h = min_height if min_height is not None else rules["min_height"]

    try:
        with Image.open(resolved) as img:
            img.load()
            report.width, report.height = img.size
            report.format = img.format or resolved.suffix.lstrip(".").upper()
            report.color_mode = img.mode

            if report.width < effective_min_w or report.height < effective_min_h:
                report.messages.append(
                    f"dimensões {report.width}x{report.height} abaixo do mínimo "
                    f"{effective_min_w}x{effective_min_h}"
                )
                return report

            pixels = list(img.getdata())
            sample_size = min(len(pixels), 5000)
            sample = pixels[:sample_size]
            report.unique_colors_sampled = len(set(sample))

            if report.color_mode in ("RGB", "RGBA"):
                report.is_blank = report.unique_colors_sampled <= 1
                if report.is_blank:
                    report.messages.append(
                        "imagem contém apenas uma cor — provável arquivo corrompido ou vazio"
                    )
                    return report

                if all(
                    pixel[:3] == (255, 255, 255)
                    for pixel in sample
                    if isinstance(pixel, tuple)
                ):
                    report.messages.append(
                        "amostra de pixels é inteiramente branca — upload seria inválido"
                    )
                    return report

            report.valid = True
            return report

    except Exception as error:
        report.messages.append(f"falha ao abrir imagem: {error}")
        return report
