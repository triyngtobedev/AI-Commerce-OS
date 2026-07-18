#!/usr/bin/env python3
"""Smoke test das melhorias de qualidade YouTube (queries EN + director)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from scripts.video.asset_search import generate_asset_queries
from scripts.video.query_localizer import is_critical_scene, looks_portuguese
from scripts.youtube.youtube_scenes import generate_youtube_scenes


def main() -> int:
    topic = {
        "nome": "Operacao Barbarossa",
        "keywords": ["barbarossa", "ww2", "eastern front"],
    }
    content = {
        "texto_narracao": (
            "Em 1941 a Alemanha invadiu a Uniao Sovietica na Operacao Barbarossa. "
            "Milhoes de soldados cruzaram a fronteira oriental."
        ),
    }
    strategy = {
        "queries_contexto": [
            "Operacao Barbarossa 1941 mapa fronte oriental",
            "tropas alemas invasao URSS",
        ],
        "angulo": "cronologia_epica",
    }

    scenes = generate_youtube_scenes(topic, content, strategy)
    queries = generate_asset_queries(scenes, platform="youtube_dark")

    print("=== Smoke: queries localizadas ===")
    errors = 0
    for query in queries:
        busca = query["busca"]
        tipo = query["tipo"]
        print(f"  [{tipo}] {busca}")
        print(
            f"    critica={is_critical_scene(tipo)} "
            f"asset={query.get('primary_asset')} "
            f"pt={looks_portuguese(busca)}"
        )
        if looks_portuguese(busca) and "historical" not in busca.lower():
            print("    ERRO: query ainda parece portugues")
            errors += 1
        if query.get("visual_direction"):
            print(f"    director={query['visual_direction'].get('visual_type')}")

    print()
    print(f"USE_N8N_FOR_SCENES={os.getenv('USE_N8N_FOR_SCENES', 'false')}")
    print(f"REPLICATE={'ok' if os.getenv('REPLICATE_API_TOKEN') else 'missing'}")
    print(f"HF={'ok' if os.getenv('HF_API_TOKEN') else 'missing'}")

    if errors:
        print(f"\nFALHOU: {errors} queries com problema")
        return 1

    print(f"\nOK: {len(queries)} cenas processadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
