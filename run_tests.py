"""
Runner de testes completo do ai-commerce-os.

Uso:
  python run_tests.py              # suite padrão (rápida, sem integrações)
  python run_tests.py all          # todas as suites incluindo scripts/**/test_*.py
  python run_tests.py fast         # só api/tests/ e tests/ (mais rápido ainda)
  python run_tests.py api          # só testes da API
  python run_tests.py scripts      # só testes em scripts/
  python run_tests.py cov          # suite padrão + relatório de cobertura HTML
  python run_tests.py discover     # lista todos os arquivos test_*.py encontrados
"""
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
os.environ.setdefault("PYTHONPATH", str(ROOT))
os.environ.setdefault("PIPELINE_API_KEY", "test-key-local")
os.environ.setdefault("YOUTUBE_AUTO_UPLOAD", "false")
os.environ.setdefault("YOUTUBE_DRY_RUN", "true")
os.environ.setdefault("USE_N8N_FOR_SCENES", "false")

for d in ["database", "output", "reports", "logs"]:
    (ROOT / d).mkdir(exist_ok=True)

SUITE_API = [
    "api/tests/",
]

SUITE_CORE = [
    "tests/",
    "scripts/ai/test_router.py",
    "scripts/utils/test_json_parser.py",
    "scripts/utils/test_prompt.py",
    "scripts/core/test_brand_kit.py",
    "scripts/core/test_brand_validation.py",
    "scripts/core/test_director_engine.py",
    "scripts/core/test_emotional_timeline.py",
    "scripts/core/test_timeline_integrations.py",
    "scripts/core/test_timeline_sync.py",
    "scripts/core/test_visual_intent_engine.py",
    "scripts/core/production/test_production.py",
    "scripts/core/production/test_quality_score.py",
    "scripts/core/production/test_rerun_mode.py",
]

SUITE_AUDIO = [
    "scripts/audio/test_azure_tts_provider.py",
    "scripts/audio/test_emotion_mapper.py",
    "scripts/audio/test_narration_engine.py",
    "scripts/audio/test_soundtrack_engine.py",
    "scripts/audio/test_ssml_builder.py",
    "scripts/audio/test_tts_text_prep.py",
    "scripts/audio/test_voice_engine.py",
]

SUITE_CREATIVE = [
    "scripts/creative/test_ai_script.py",
    "scripts/creative/test_script_generator.py",
    "scripts/creative/test_script_parser.py",
]

SUITE_VIDEO = [
    "scripts/video/test_asset_ranking.py",
    "scripts/video/test_media_engine_fast.py",
    "scripts/video/test_media_search.py",
    "scripts/video/test_pixabay_provider.py",
    "scripts/video/test_scene_timeline.py",
    "scripts/video/test_subtitle_engine.py",
    "scripts/video/test_wikimedia_provider.py",
    "scripts/video/media_providers/huggingface/test_hf_provider.py",
]

SUITE_YOUTUBE = [
    "scripts/youtube/test_lofi_dark.py",
    "scripts/youtube/test_narration_utils.py",
    "scripts/youtube/test_thumbnail_generator.py",
    "scripts/youtube/test_topic_selector.py",
]

SUITE_PUBLISHER = [
    "scripts/publisher/test_exporter.py",
    "scripts/publisher/test_youtube_auth.py",
    "scripts/publisher/test_youtube_publication.py",
    "scripts/publisher/test_youtube_publish_config.py",
]

SUITE_MISC = [
    "scripts/affiliate/test_opportunity.py",
    "scripts/content/test_content.py",
    "scripts/persona/test_persona.py",
    "scripts/persona/test_persona_render.py",
    "database/test_database.py",
]

SUITE_E2E = [
    "scripts/youtube/test_youtube_pipeline_e2e.py",
    "scripts/youtube/test_youtube_scenes.py",
    "scripts/ai/analysts/test_ai_analyst.py",
]

DEFAULT_SUITE = (
    SUITE_API
    + SUITE_CORE
    + SUITE_AUDIO
    + SUITE_CREATIVE
    + SUITE_VIDEO
    + SUITE_YOUTUBE
    + SUITE_PUBLISHER
    + SUITE_MISC
)

COMMON_FLAGS = [
    "-q",
    "--tb=short",
    "-k",
    "not integration and not slow and not e2e and not smoke",
]


def run(targets: list[str], extra_flags: list[str] | None = None) -> int:
    existing = [t for t in targets if Path(ROOT / t).exists()]
    missing = set(targets) - set(existing)
    if missing:
        print(f"[aviso] Ignorados (não encontrados): {', '.join(sorted(missing))}")

    cmd = [sys.executable, "-m", "pytest"] + existing + COMMON_FLAGS + (extra_flags or [])
    print(f"\n{'─'*60}")
    print(f"Rodando {len(existing)} suites de teste...")
    print(f"{'─'*60}\n")
    return subprocess.run(cmd, cwd=ROOT).returncode


def discover() -> None:
    print("\nArquivos test_*.py encontrados no projeto:\n")
    found = sorted(ROOT.rglob("test_*.py"))
    for f in found:
        rel = f.relative_to(ROOT)
        print(f"  {rel}")
    print(f"\nTotal: {len(found)} arquivos\n")


def main() -> None:
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "default"

    if mode == "discover":
        discover()
        return

    if mode == "fast":
        code = run(SUITE_API + ["tests/"])
    elif mode == "api":
        code = run(SUITE_API)
    elif mode == "scripts":
        code = run(
            SUITE_AUDIO
            + SUITE_CREATIVE
            + SUITE_VIDEO
            + SUITE_YOUTUBE
            + SUITE_PUBLISHER
            + SUITE_MISC
            + SUITE_CORE
        )
    elif mode == "all":
        code = run(DEFAULT_SUITE + SUITE_E2E, ["-k", ""])
    elif mode == "cov":
        code = run(
            DEFAULT_SUITE,
            [
                "--cov=api",
                "--cov=src",
                "--cov=scripts",
                "--cov-report=html:coverage_html",
                "--cov-report=term-missing",
            ],
        )
        if code == 0:
            print("\nRelatório de cobertura gerado em: coverage_html/index.html")
    else:
        code = run(DEFAULT_SUITE)

    sys.exit(code)


if __name__ == "__main__":
    main()
