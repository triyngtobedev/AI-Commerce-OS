"""
Abstração unificada de sujeito de conteúdo.

Tanto produtos (TikTok Shop) quanto temas (YouTube) são representados
como dicionários compatíveis, permitindo reutilização dos engines.
"""

from typing import Any, Dict


REQUIRED_FIELDS = ("nome", "categoria")


def normalize_subject(
    data: Dict[str, Any],
    content_type: str = "product",
) -> Dict[str, Any]:
    """
    Normaliza um sujeito de conteúdo para o formato interno.

    Produtos e temas compartilham os campos base:
        nome, categoria

    Campos opcionais comuns:
        keywords, score_tecnico, subcategoria
    """

    subject = dict(data)

    subject["_content_type"] = content_type

    for field in REQUIRED_FIELDS:
        if field not in subject:
            raise ValueError(
                f"Campo obrigatório ausente no sujeito: {field}"
            )

    return subject


def get_subject_name(subject: Dict[str, Any]) -> str:
    """Retorna o nome/título do sujeito."""

    return subject.get("nome", "conteudo")


def is_topic(subject: Dict[str, Any]) -> bool:
    """Verifica se o sujeito é um tema (YouTube)."""

    return subject.get("_content_type") == "topic"


def is_product(subject: Dict[str, Any]) -> bool:
    """Verifica se o sujeito é um produto (TikTok)."""

    return subject.get("_content_type", "product") == "product"
