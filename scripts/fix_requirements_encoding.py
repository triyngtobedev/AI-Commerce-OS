"""
Corrige o encoding do requirements.txt de UTF-16 para UTF-8.
Uso: python scripts/fix_requirements_encoding.py
"""
import sys
from pathlib import Path


def fix_encoding(path: str = "requirements.txt") -> None:
    req = Path(path)
    if not req.exists():
        print(f"Arquivo não encontrado: {path}")
        sys.exit(1)

    raw = req.read_bytes()

    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        print(f"{path} detectado como UTF-16 — convertendo para UTF-8...")
        encoding = "utf-16"
    else:
        try:
            raw.decode("utf-8")
            print(f"{path} já está em UTF-8. Nenhuma ação necessária.")
            return
        except UnicodeDecodeError:
            encoding = "utf-16"
            print(f"{path} parece ter encoding inválido — tentando UTF-16...")

    content = raw.decode(encoding)
    req.write_text(content, encoding="utf-8")
    print(f"Convertido com sucesso para UTF-8 ({len(content.splitlines())} linhas).")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    fix_encoding(target)
