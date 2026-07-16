"""
MediaAsset — tipo interno normalizado de mídia (imagem/vídeo).

Este é o "formato canônico" que o restante do AI-Commerce-OS consome.
Provedores (Hugging Face, Pollinations, stock) devem *normalizar* suas respostas
brutas para este tipo, de modo que o pipeline nunca dependa do shape cru de
uma API externa. Isso resolve a classe de bugs de "formatos incompatíveis":
MIME types errados, campos faltando e shapes inesperados são absorvidos na
fronteira do provedor, e o downstream sempre recebe um MediaAsset previsível.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MediaKind(str, Enum):
    """Tipo de mídia normalizado. Herda de str para serializar direto em JSON."""

    IMAGE = "image"
    VIDEO = "video"


@dataclass(frozen=True)
class MediaAsset:
    """
    Representação imutável de um asset de mídia já materializado em disco.

    `frozen=True` porque um asset, uma vez validado e salvo, não deve ser
    mutado silenciosamente por consumidores — qualquer transformação deve
    produzir um novo MediaAsset, mantendo a rastreabilidade da origem.

    Campos obrigatórios cobrem o mínimo que todo consumidor precisa
    (tipo, caminho local, dimensões, MIME e origem). Campos opcionais
    carregam metadados específicos de vídeo ou de proveniência.
    """

    kind: MediaKind
    path: Path
    width: int
    height: int
    mime_type: str
    source: str  # identificador do provedor, ex.: "huggingface"

    # Metadados opcionais / específicos de vídeo
    duration_seconds: float | None = None
    has_audio: bool | None = None
    prompt: str | None = None
    remote_url: str | None = None  # URL assinada (expira) de onde o asset veio
    expires_at: str | None = None  # ISO-8601, quando a URL remota expira
    seed: int | None = None
    file_size_bytes: int = 0

    @property
    def is_image(self) -> bool:
        return self.kind is MediaKind.IMAGE

    @property
    def is_video(self) -> bool:
        return self.kind is MediaKind.VIDEO

    def to_dict(self) -> dict:
        """Serializa para dict JSON-friendly (ex.: para media_search.json)."""

        return {
            "kind": self.kind.value,
            "path": str(self.path),
            "width": self.width,
            "height": self.height,
            "mime_type": self.mime_type,
            "source": self.source,
            "duration_seconds": self.duration_seconds,
            "has_audio": self.has_audio,
            "prompt": self.prompt,
            "remote_url": self.remote_url,
            "expires_at": self.expires_at,
            "seed": self.seed,
            "file_size_bytes": self.file_size_bytes,
        }
