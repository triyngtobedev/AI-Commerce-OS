import re
import unicodedata

from pathlib import Path


def slugify(text):
    """
    Converte texto em slug seguro para paths.
    Remove acentos e normaliza separadores.
    """

    text = str(text).strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = re.sub(
        r"[^\w\s\-]",
        "",
        text
    )

    text = re.sub(
        r"[\s_/\\]+",
        "-",
        text
    )

    text = re.sub(
        r"-+",
        "-",
        text
    )

    return text.strip("-")


def product_output_dir(product, base="output"):
    """
    Retorna o diretório de saída padronizado do produto.
    """

    return content_output_dir(product, base)


def content_output_dir(subject, base="output", platform=None):
    """
    Retorna o diretório de saída padronizado do conteúdo.

    Quando platform é informada, prefixa o slug para evitar
    colisão entre pipelines (ex: tiktok/produto-x vs youtube/produto-x).
    """

    name = subject.get(
        "nome",
        "conteudo"
    )

    slug = slugify(name)

    if platform:
        return Path(base) / platform / slug

    return Path(base) / slug
