import os
import re
import unicodedata

from pathlib import Path

PERSISTENT_OUTPUT_ROOT = Path("/app/persistent/output")
DEFAULT_LOCAL_OUTPUT = Path("output")


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


def get_output_base() -> Path:
    """
    Diretório base de saída do pipeline.

    Prioridade:
      1. OUTPUT_DIR (Railway entrypoint define /app/persistent/output)
      2. /app/persistent/output quando o volume estiver montado
      3. output/ relativo (dev local)
    """
    configured = os.getenv("OUTPUT_DIR", "").strip()
    if configured:
        base = Path(configured)
    elif PERSISTENT_OUTPUT_ROOT.parent.is_dir():
        base = PERSISTENT_OUTPUT_ROOT
    else:
        base = DEFAULT_LOCAL_OUTPUT

    base.mkdir(parents=True, exist_ok=True)
    return base


def product_output_dir(product, base=None):
    """
    Retorna o diretório de saída padronizado do produto.
    """

    return content_output_dir(product, base)


def content_output_dir(subject, base=None, platform=None):
    """
    Retorna o diretório de saída padronizado do conteúdo.

    Quando platform é informada, prefixa o slug para evitar
    colisão entre pipelines (ex: tiktok/produto-x vs youtube/produto-x).
    """

    if base is None:
        base = get_output_base()
    else:
        base = Path(base)

    name = subject.get(
        "nome",
        "conteudo"
    )

    slug = slugify(name)

    if platform:
        path = base / platform / slug
    else:
        path = base / slug

    path.mkdir(parents=True, exist_ok=True)
    return path
