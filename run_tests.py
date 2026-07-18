#!/usr/bin/env python3
"""
Runner de testes cross-platform.

Garante que a raiz do repositório está no PYTHONPATH antes de importar `scripts`.
Use a partir de qualquer diretório:

    python run_tests.py
    python run_tests.py scripts.youtube.test_lofi_dark
    python run_tests.py discover
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROOT_STR = str(ROOT)

if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)


DEFAULT_MODULES = (
    "scripts.youtube.test_lofi_dark",
    "scripts.youtube.test_template_override",
    "scripts.youtube.test_youtube_scenes",
)


def _run_named_tests(modules: list[str]) -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    errors: list[str] = []

    for module_name in modules:
        try:
            suite.addTests(loader.loadTestsFromName(module_name))
        except Exception as exc:
            errors.append(f"{module_name}: {exc}")

    if errors:
        print("Falha ao carregar testes:\n", file=sys.stderr)
        for message in errors:
            print(f"  - {message}", file=sys.stderr)
        print(
            f"\nRaiz do repo: {ROOT}\n"
            "Execute a partir da raiz:\n"
            f"  cd {ROOT}\n"
            "  python run_tests.py\n"
            "Ou de infra/:\n"
            "  .\\run_tests.ps1\n",
            file=sys.stderr,
        )
        return 1

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def _run_discover() -> int:
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "scripts"),
        pattern="test_*.py",
        top_level_dir=ROOT_STR,
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])

    if not args:
        return _run_named_tests(list(DEFAULT_MODULES))

    if args == ["discover"]:
        return _run_discover()

    return _run_named_tests(args)


if __name__ == "__main__":
    raise SystemExit(main())
