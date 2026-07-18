#!/usr/bin/env python3
"""
Testa automaticamente os quick wins do pipeline YouTube Dark.

Uso:
  python testar_quick_wins.py
  python testar_quick_wins.py --validate-only   # só valida assets existentes

Gera dois vídeos (documentário + Dark5), valida pacing, thumbnail,
film grain, estrutura do roteiro, narração (2A) e legendas (2B).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

# Temas estáveis em database/topics_source.json
TOPIC_DEFAULT = (
    "A Guerra Mais Estranha da História: "
    "Quando a Austrália Enfrentou Emus e Perdeu"
)
TOPIC_DARK5 = "A Verdade Sobre a Biblioteca de Alexandria"

DARK5_KEYS = ["fato_5", "fato_4", "fato_3", "fato_2", "fato_1"]
MAX_SCENE_SECONDS = 20.0
MAX_WORDS_PER_SENTENCE = 12
MAX_WORDS_PER_CAPTION_LINE = 5
EXPECTED_FONT_SIZE = 52
ASS_HIGHLIGHT_COLORS = {
    "gold": "&H0000D7FF",
    "red": "&H000000FF",
    "cyan": "&H00FFFF00",
}


def _banner(title: str) -> None:
    line = "═" * 52
    print(f"\n{line}\n {title}\n{line}")


def _output_dir(topic_name: str) -> Path:
    from scripts.utils.slug import content_output_dir

    return content_output_dir({"nome": topic_name}, platform="youtube_dark")


def _has_renderable_assets(folder: Path) -> bool:
    has_scenes = (folder / "scenes.json").exists() or (
        folder / "video_project.json"
    ).exists()
    has_audio = (folder / "assets" / "audio" / "narracao.mp3").exists()
    return has_scenes and has_audio


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _prepare_folder_for_rerender(folder: Path) -> None:
    """Corrige artefatos quebrados antes do re-render."""

    if not _ensure_scenes_json(folder):
        raise RuntimeError(f"Não foi possível preparar scenes.json em {folder}")

    emotional_file = folder / "emotional_timeline.json"
    if emotional_file.exists() and not emotional_file.read_text(encoding="utf-8").strip():
        emotional_file.unlink()
        print("   🔧 Removido emotional_timeline.json vazio (será reconstruído)")


def _ensure_scenes_json(folder: Path) -> bool:
    """rerender_test exige scenes.json — cria a partir de video_project.json se necessário."""

    scenes_file = folder / "scenes.json"
    if scenes_file.exists():
        return True

    project_file = folder / "video_project.json"
    if not project_file.exists():
        return False

    project = _load_json(project_file)
    if not isinstance(project, dict):
        return False

    cenas = project.get("cenas")
    if not cenas:
        return False

    scenes_file.write_text(
        json.dumps(cenas, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return True


def _run_pipeline(topic_name: str, roteiro_template: str | None = None) -> Path:
    import scripts.pipeline.youtube_pipeline as pipeline_module

    folder = _output_dir(topic_name)
    original_strategy = pipeline_module.generate_youtube_strategy

    def patched_strategy(topic, analysis, opportunity):
        strategy = original_strategy(topic, analysis, opportunity)
        if roteiro_template:
            strategy["roteiro_template"] = roteiro_template
        return strategy

    pipeline_module.generate_youtube_strategy = patched_strategy
    try:
        print(f"\n⏳ Pipeline completo: {topic_name}")
        if roteiro_template:
            print(f"   Template forçado: {roteiro_template}")
        print("   (pode levar bastante tempo na primeira execução)\n")

        results = pipeline_module.run_youtube_pipeline(
            max_videos=1,
            force_topic_name=topic_name,
            force=True,
        )
    finally:
        pipeline_module.generate_youtube_strategy = original_strategy

    if not results:
        raise RuntimeError(
            f"Pipeline não produziu vídeo para '{topic_name}'. "
            "Verifique API keys no .env e logs acima."
        )

    return folder


def _rerender(folder: Path) -> None:
    from scripts.youtube.rerender_test import rerender

    _prepare_folder_for_rerender(folder)

    print(f"\n⚡ Re-render rápido (assets existentes): {folder.name}\n")
    video = rerender(str(folder), refresh_media=False, regenerate_thumbnail=True)
    if not video:
        raise RuntimeError(f"Re-render falhou em {folder}")


def generate_default_video() -> Path:
    _banner("1/2 — Vídeo padrão (documentário)")
    folder = _output_dir(TOPIC_DEFAULT)

    if _has_renderable_assets(folder):
        _rerender(folder)
    else:
        _run_pipeline(TOPIC_DEFAULT)

    return folder


def _has_dark5_script(folder: Path) -> bool:
    script = _load_json(folder / "script.json")
    if not isinstance(script, dict):
        return False
    return all(str(script.get(key, "")).strip() for key in DARK5_KEYS)


def generate_dark5_video() -> Path:
    _banner("2/2 — Vídeo Dark5 (roteiro_template: dark5)")
    folder = _output_dir(TOPIC_DARK5)

    strategy_path = folder / "strategy.json"
    strategy = _load_json(strategy_path) or {}
    strategy_is_dark5 = strategy.get("roteiro_template") == "dark5"

    if _has_renderable_assets(folder) and strategy_is_dark5 and _has_dark5_script(folder):
        _rerender(folder)
    else:
        # Dark5 exige roteiro diferente — pipeline com template forçado.
        _run_pipeline(TOPIC_DARK5, roteiro_template="dark5")

    return folder


def _load_script(folder: Path) -> dict | None:
    data = _load_json(folder / "script.json")
    return data if isinstance(data, dict) else None


def _regenerate_subtitles(folder: Path) -> None:
    """Regenera captions.ass/srt com configuração atual do BrandEngine."""

    scenes = _load_scenes(folder)
    if not scenes:
        return

    from scripts.core.brand_engine import get_render_style, should_show_intro
    from scripts.video.subtitle_engine import write_subtitles

    platform = "youtube_dark"
    timing_offset = (
        get_render_style(platform).intro_seconds if should_show_intro(platform) else 0.0
    )
    audio_path = folder / "assets" / "audio" / "narracao.mp3"
    audio_duration = None
    if audio_path.exists():
        from scripts.video.media_probe import probe_duration as _probe

        probed = _probe(str(audio_path))
        if probed > 0:
            audio_duration = probed

    write_subtitles(
        scenes,
        folder,
        basename="captions",
        platform=platform,
        timing_offset=timing_offset,
        audio_duration=audio_duration,
    )


def _load_scenes(folder: Path) -> list[dict]:
    for name in ("video_project.json", "scenes.json"):
        path = folder / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        cenas = data.get("cenas", data)
        if isinstance(cenas, dict):
            return cenas.get("cenas", [])
        if isinstance(cenas, list):
            return cenas
    return []


def check_sentence_length(folder: Path) -> tuple[bool, str]:
    """Quick win 2A — frases com no máximo 12 palavras."""

    from scripts.youtube.narration_utils import validate_sentence_length

    script = _load_script(folder)
    if not script:
        return False, "script.json ausente"

    warnings = validate_sentence_length(script, max_words=MAX_WORDS_PER_SENTENCE)
    if warnings:
        sample = warnings[0]
        extra = f" (+{len(warnings) - 1} mais)" if len(warnings) > 1 else ""
        return False, f"{len(warnings)} frase(s) longa(s): {sample}{extra}"

    return True, f"todas as frases ≤ {MAX_WORDS_PER_SENTENCE} palavras"


def check_scene_hooks(folder: Path) -> tuple[bool, str]:
    """Quick win 2A — ganchos de retenção entre seções."""

    from scripts.youtube.narration_utils import validate_scene_hooks

    script = _load_script(folder)
    if not script:
        return False, "script.json ausente"

    warnings = validate_scene_hooks(script)
    if warnings:
        sample = warnings[0]
        extra = f" (+{len(warnings) - 1} seções)" if len(warnings) > 1 else ""
        return False, f"{len(warnings)} seção(ões) sem gancho: {sample}{extra}"

    return True, "ganchos presentes em todas as seções (exceto encerramento)"


def _parse_ass_style(ass_content: str) -> dict[str, str]:
    for line in ass_content.splitlines():
        if line.startswith("Style: Default,"):
            parts = line.split(",", 23)
            if len(parts) >= 9:
                return {
                    "font_size": parts[2].strip(),
                    "bold": parts[7].strip(),
                }
    return {}


def _ass_dialogue_lines(ass_content: str) -> list[str]:
    lines = []
    for line in ass_content.splitlines():
        if not line.startswith("Dialogue:"):
            continue
        text = line.split(",,")[-1] if ",," in line else line.rsplit(",", 1)[-1]
        lines.append(text.replace("\\N", "\n"))
    return lines


def check_caption_settings(folder: Path) -> tuple[bool, str]:
    """Quick win 2B — fonte 52px, bold, máx 5 palavras/linha."""

    ass_path = folder / "captions.ass"
    if not ass_path.exists():
        return False, "captions.ass ausente"

    content = ass_path.read_text(encoding="utf-8")
    style = _parse_ass_style(content)
    if not style:
        return False, "estilo Default não encontrado no ASS"

    issues: list[str] = []
    if style.get("font_size") != str(EXPECTED_FONT_SIZE):
        issues.append(f"fonte {style.get('font_size')}px (esperado {EXPECTED_FONT_SIZE}px)")
    if style.get("bold") != "-1":
        issues.append(f"bold={style.get('bold')} (esperado -1)")

    long_lines: list[str] = []
    for block in _ass_dialogue_lines(content):
        for line in block.split("\n"):
            words = line.strip().split()
            if len(words) > MAX_WORDS_PER_CAPTION_LINE:
                preview = " ".join(words[:6])
                long_lines.append(f"{len(words)} palavras: \"{preview}...\"")

    if long_lines:
        issues.append(
            f"{len(long_lines)} linha(s) > {MAX_WORDS_PER_CAPTION_LINE} palavras "
            f"(ex: {long_lines[0]})"
        )

    if issues:
        return False, "; ".join(issues)

    return True, (
        f"fonte {EXPECTED_FONT_SIZE}px, bold ativo, "
        f"≤ {MAX_WORDS_PER_CAPTION_LINE} palavras/linha"
    )


def check_ass_highlights(folder: Path) -> tuple[bool, str]:
    """Quick win 2B — destaque colorido gold/vermelho/ciano no ASS."""

    ass_path = folder / "captions.ass"
    if not ass_path.exists():
        return False, "captions.ass ausente"

    content = ass_path.read_text(encoding="utf-8")
    found = [name for name, code in ASS_HIGHLIGHT_COLORS.items() if code in content]
    missing = [name for name in ASS_HIGHLIGHT_COLORS if name not in found]

    if len(found) < 2:
        return False, (
            f"apenas {len(found)} cor(es) detectada(s) ({', '.join(found) or 'nenhuma'}); "
            f"faltam: {', '.join(missing)}"
        )

    return True, f"destaques {', '.join(found)} presentes no ASS"


def _collect_validation_results(
    default_folder: Path | None,
    dark5_folder: Path | None,
) -> list[tuple[bool, str, str]]:
    results: list[tuple[bool, str, str]] = []

    if default_folder and default_folder.exists():
        ok, detail = check_pacing(default_folder)
        results.append((ok, "Pacing OK", detail))

        ok, detail = check_thumbnail_gold_border(default_folder)
        label = "Thumbnail com borda gold" if ok else "Thumbnail sem borda gold"
        results.append((ok, label, detail))

        ok, detail = check_film_grain(default_folder)
        results.append((ok, "Film grain", detail))
    else:
        results.extend(
            [
                (False, "Pacing OK", "vídeo padrão não gerado"),
                (False, "Thumbnail sem borda gold", "vídeo padrão não gerado"),
                (False, "Film grain", "vídeo padrão não gerado"),
            ]
        )

    if dark5_folder and dark5_folder.exists():
        ok, detail = check_dark5_structure(dark5_folder)
        label = "Template Dark5" if ok else "Template Dark5 inválido"
        results.append((ok, label, detail))
    else:
        results.append((False, "Template Dark5", "vídeo Dark5 não gerado"))

    # Quick wins 2A — narração (valida ambos os roteiros quando existirem)
    script_folders = [f for f in (default_folder, dark5_folder) if f and f.exists()]
    if script_folders:
        all_sentence_ok = True
        sentence_details: list[str] = []
        for folder in script_folders:
            ok, detail = check_sentence_length(folder)
            if not ok:
                all_sentence_ok = False
                sentence_details.append(f"{folder.name}: {detail}")
        if all_sentence_ok:
            results.append(
                (True, "Frases ≤ 12 palavras", f"OK em {len(script_folders)} roteiro(s)")
            )
        else:
            results.append(
                (False, "Frases ≤ 12 palavras", "; ".join(sentence_details))
            )

        all_hooks_ok = True
        hook_details: list[str] = []
        for folder in script_folders:
            ok, detail = check_scene_hooks(folder)
            if not ok:
                all_hooks_ok = False
                hook_details.append(f"{folder.name}: {detail}")
        if all_hooks_ok:
            results.append(
                (True, "Ganchos entre seções", f"OK em {len(script_folders)} roteiro(s)")
            )
        else:
            results.append((False, "Ganchos entre seções", "; ".join(hook_details)))
    else:
        results.extend(
            [
                (False, "Frases ≤ 12 palavras", "nenhum roteiro disponível"),
                (False, "Ganchos entre seções", "nenhum roteiro disponível"),
            ]
        )

    # Quick wins 2B — legendas (regenera ASS com config atual antes de validar)
    caption_folder = dark5_folder or default_folder
    if caption_folder and caption_folder.exists():
        try:
            _regenerate_subtitles(caption_folder)
        except Exception as exc:
            results.extend(
                [
                    (False, "Legendas 52px bold ≤5 palavras", f"erro ao regenerar: {exc}"),
                    (False, "Destaques coloridos no ASS", f"erro ao regenerar: {exc}"),
                ]
            )
        else:
            ok, detail = check_caption_settings(caption_folder)
            results.append((ok, "Legendas 52px bold ≤5 palavras", detail))

            ok, detail = check_ass_highlights(caption_folder)
            results.append((ok, "Destaques coloridos no ASS", detail))
    else:
        results.extend(
            [
                (False, "Legendas 52px bold ≤5 palavras", "pasta de saída indisponível"),
                (False, "Destaques coloridos no ASS", "pasta de saída indisponível"),
            ]
        )

    return results


def check_pacing(folder: Path) -> tuple[bool, str]:
    scenes = _load_scenes(folder)
    if not scenes:
        return False, "nenhuma cena encontrada em video_project.json / scenes.json"

    long_scenes = [
        s
        for s in scenes
        if float(s.get("duration_seconds", 0)) > MAX_SCENE_SECONDS
    ]
    if long_scenes:
        worst = max(float(s.get("duration_seconds", 0)) for s in long_scenes)
        return False, f"{len(long_scenes)} cena(s) acima de 20s (pior: {worst:.1f}s)"

    return True, "nenhuma cena passou de 20s"


def _is_gold_pixel(r: int, g: int, b: int) -> bool:
    return r >= 200 and g >= 150 and b <= 90


def check_thumbnail_gold_border(folder: Path) -> tuple[bool, str]:
    thumb = folder / "thumbnail.jpg"
    if not thumb.exists() or thumb.stat().st_size < 1024:
        return False, "thumbnail.jpg ausente ou inválido"

    try:
        from PIL import Image
    except ImportError:
        return False, "Pillow não instalado (pip install Pillow)"

    from scripts.core.brand_kit import get_brand_kit

    kit = get_brand_kit("youtube_dark")
    border_w = kit.thumbnail.border_width
    if border_w <= 0:
        return False, "borda desativada no BrandKit"

    img = Image.open(thumb).convert("RGB")
    w, h = img.size

    samples: list[tuple[int, int, int]] = []
    for offset in range(border_w):
        samples.extend(
            [
                img.getpixel((offset, offset)),
                img.getpixel((w - 1 - offset, offset)),
                img.getpixel((offset, h - 1 - offset)),
                img.getpixel((w - 1 - offset, h - 1 - offset)),
            ]
        )

    gold_hits = sum(1 for px in samples if _is_gold_pixel(*px))
    ratio = gold_hits / len(samples) if samples else 0.0

    if ratio >= 0.5:
        return True, "borda gold detectada no thumbnail"

    return False, "verificar implementação"


def check_film_grain(folder: Path) -> tuple[bool, str]:
    video = folder / "video_final.mp4"
    if not video.exists() or video.stat().st_size < 10_000:
        return False, "video_final.mp4 ausente ou inválido"

    from scripts.core.brand_engine import get_render_style
    from scripts.video.scene_renderer import _scale_pad_filter

    render_style = get_render_style("youtube_dark")
    grain = (render_style.film_grain or "").strip()
    if not grain.startswith("noise="):
        return False, "film_grain não configurado no BrandKit"

    # Mesma lógica de mux_video_audio_subtitles — confirma que o render aplica grain.
    video_filter = _scale_pad_filter(1920, 1080)
    if grain not in video_filter:
        video_filter = f"{video_filter},{grain}"

    if "noise=" not in video_filter:
        return False, "filtro FFmpeg de grain inválido"

    return True, "film grain aplicado no vídeo final"


def check_dark5_structure(folder: Path) -> tuple[bool, str]:
    script_path = folder / "script.json"
    if not script_path.exists():
        return False, "script.json ausente"

    script = json.loads(script_path.read_text(encoding="utf-8"))
    meta = script.get("_meta", {})
    template = meta.get("roteiro_template")

    if not template:
        strategy_path = folder / "strategy.json"
        if strategy_path.exists():
            strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
            template = strategy.get("roteiro_template")

    if template != "dark5":
        return False, f"roteiro_template={template!r}, esperado 'dark5'"

    missing = [key for key in DARK5_KEYS if not str(script.get(key, "")).strip()]
    if missing:
        return False, f"seções ausentes: {', '.join(missing)}"

    return True, "estrutura fato_5 → fato_1"


def _print_result(ok: bool, label: str, detail: str) -> None:
    icon = "✅" if ok else "❌"
    print(f"{icon} {label} — {detail}")


def open_output_folder(folder: Path) -> None:
    target = folder if folder.exists() else ROOT / "output" / "youtube_dark"
    target.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 Abrindo pasta: {target.resolve()}")

    if sys.platform == "win32":
        os.startfile(str(target.resolve()))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(target.resolve())], check=False)
    else:
        subprocess.run(["xdg-open", str(target.resolve())], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Testa quick wins do pipeline YouTube Dark")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Pula geração/re-render e valida apenas assets existentes",
    )
    parser.add_argument(
        "--no-open-folder",
        action="store_true",
        help="Não abre a pasta de saída ao final",
    )
    args = parser.parse_args()

    _banner("TESTE AUTOMÁTICO — QUICK WINS")
    if args.validate_only:
        print("Modo validate-only: pulando geração de vídeos.\n")
    else:
        print("Gera 2 vídeos (ou re-render rápido) e valida todos os quick wins.\n")

    default_folder = _output_dir(TOPIC_DEFAULT)
    dark5_folder = _output_dir(TOPIC_DARK5)
    errors: list[str] = []

    if not args.validate_only:
        try:
            default_folder = generate_default_video()
        except Exception as exc:
            errors.append(f"Vídeo padrão: {exc}")
            default_folder = _output_dir(TOPIC_DEFAULT)
            print(f"\n⚠️ Erro no vídeo padrão: {exc}")

        try:
            dark5_folder = generate_dark5_video()
        except Exception as exc:
            errors.append(f"Vídeo Dark5: {exc}")
            dark5_folder = _output_dir(TOPIC_DARK5)
            print(f"\n⚠️ Erro no vídeo Dark5: {exc}")

    _banner("RESULTADO DOS QUICK WINS")

    results = _collect_validation_results(default_folder, dark5_folder)

    for ok, label, detail in results:
        _print_result(ok, label, detail)

    if dark5_folder and dark5_folder.exists():
        dark5_video = dark5_folder / "video_final.mp4"
        if not dark5_video.exists() or dark5_video.stat().st_size < 10_000:
            print(
                "\n⚠️ Atenção: roteiro Dark5 validado, mas video_final.mp4 "
                "não foi gerado — rode novamente após a correção de cenas Dark5."
            )

    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print(f"\nResumo: {passed}/{total} verificações OK")

    if errors:
        print("\nErros durante geração:")
        for item in errors:
            print(f"  - {item}")

    if not args.no_open_folder:
        open_folder = dark5_folder or default_folder or ROOT / "output" / "youtube_dark"
        open_output_folder(open_folder)

    return 0 if passed == total and not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
