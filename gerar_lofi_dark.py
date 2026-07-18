#!/usr/bin/env python3
"""Comando descontinuado — todo processamento roda no Railway."""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("❌ gerar_lofi_dark.py na raiz foi descontinuado.")
print("   Todo processamento roda na nuvem (Railway).")
print("")
print('   python scripts/cloud/gerar_video.py --topic "SEU TEMA" --template lofi_dark')
print("")
print("   (Debug local de devs: scripts/dev/gerar_lofi_dark.py — não usar em produção)")
raise SystemExit(1)
