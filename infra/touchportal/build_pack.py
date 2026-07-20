#!/usr/bin/env python3
"""
Gera o pacote importavel do Touch Portal para AI-Commerce-OS.

Saida:
  infra/touchportal/dist/AI-Commerce-OS-Panels.tpz   (use este no import)
  infra/touchportal/dist/AI-Commerce-OS-Panels.tpz2 (alias)

Uso:
    python infra/touchportal/build_pack.py
    python infra/touchportal/build_pack.py --project-root "D:\\Dev\\AI-Commerce-OS"
"""

from __future__ import annotations

import argparse
import json
import random
import string
import struct
import time
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "dist"

COLOR_PAGE_BG = (12, 18, 32)
COLOR_BTN = (24, 36, 64)
COLOR_BTN_ACCENT = (255, 183, 3)
COLOR_BTN_GIT = (45, 106, 79)
COLOR_BTN_DANGER = (120, 45, 45)
COLOR_TEXT = (255, 255, 255)

GRID_SIZE = 15


def rgb_to_tp(r: int, g: int, b: int, a: int = 255) -> int:
    value = (a << 24) | (r << 16) | (g << 8) | b
    if value >= 0x80000000:
        value -= 0x100000000
    return value


def _rand_id(prefix: str = "u") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{prefix}{suffix}"


@dataclass
class PlacedButton:
    row: int
    col: int
    rows: int
    cols: int
    title: str
    actions: list[dict]
    bg: tuple[int, int, int] = COLOR_BTN
    icon: str = ""


@dataclass
class PageSpec:
    key: str
    title: str
    banner: str
    rows: int
    cols: int
    buttons: list[PlacedButton] = field(default_factory=list)


class PageBuilder:
    def __init__(self, spec: PageSpec, *, page_bg: tuple[int, int, int] = COLOR_PAGE_BG):
        self.spec = spec
        self.page_bg = page_bg
        self.key_id = str(int(time.time() * 1000) + random.randint(0, 999))[-13:]

    @property
    def path(self) -> str:
        return f"\\{self.key_id}.tml"

    def render(self) -> str:
        grid = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        matrix: list[list[dict | None]] = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]

        for btn in self.spec.buttons:
            row, col = btn.row, btn.col
            for rr in range(row, row + btn.rows):
                for cc in range(col, col + btn.cols):
                    if rr < GRID_SIZE and cc < GRID_SIZE:
                        grid[rr][cc] = True

            bg = rgb_to_tp(*btn.bg)
            text_color = rgb_to_tp(*COLOR_TEXT)
            matrix[row][col] = {
                "FF": "Default",
                "A": btn.actions,
                "BD": 1,
                "C": [],
                "BE": bg,
                "kSCM": 25,
                "BG": bg,
                "E": [],
                "kIAPBKC": bg,
                "I": btn.icon,
                "ITS": bool(btn.icon),
                "BiR": True,
                "kSCTY": 0,
                "BiT": True,
                "kSCHS": False,
                "inS": "",
                "IiS": not bool(btn.icon),
                "T": btn.title,
                "kSCAC": bg,
                "kSCC": text_color,
                "kSCHRC": False,
                "THO": 4,
                "id": _rand_id(),
                "GUdata": "",
                "kSCIUFATS": False,
                "kCT": 1,
                "kSIP": 0,
                "TELS": 5,
                "kSCI": "",
                "kIAs": [],
                "Ialt": "",
                "GUid": -1,
                "kSCIIVA": True,
                "COLS": btn.cols,
                "TA": 5,
                "TC": text_color,
                "kSVP": 0,
                "kSTP": 0,
                "kSVAC": text_color,
                "TO": 4,
                "TP": 2,
                "inB": False,
                "kSD": 0,
                "kSCTM": 0,
                "TS": text_color,
                "inC": 0,
                "ROWS": btn.rows,
            }

        page = {
            "kATO": "",
            "BG": rgb_to_tp(*self.page_bg),
            "MAX": False,
            "BGI": "",
            "kPL": 0,
            "kGB": True,
            "GUid": -1,
            "KEY_ID": self.key_id,
            "kATY": 0,
            "BUTTONS": matrix,
            "KEY_COLUMNS": self.spec.cols,
            "kFM": 0,
            "kBN": self.spec.banner,
            "VERSION": 1,
            "kENA": True,
            "GUdata": "",
            "KEY_TITLE": self.spec.title,
            "KEY_ROWS": self.spec.rows,
            "BTN_MARGIN": 4,
            "PO": 0,
        }
        return json.dumps(page, ensure_ascii=False, separators=(",", ":"))


class PackBuilder:
    def __init__(self, plugin_script: str):
        self.plugin_script = plugin_script.replace("/", "\\")
        self.page_paths: dict[str, str] = {}
        self.page_specs: list[PageSpec] = []

    def _goto(self, page_key: str) -> dict:
        return {
            "KEY_PAGE_NAME": self.page_paths[page_key],
            "kIEn": True,
            "KEY_TYPE": "GOTO_PAGE_ACTION",
        }

    def _run_ps(self, action: str) -> list[dict]:
        args = f'-NoProfile -ExecutionPolicy Bypass -File "{self.plugin_script}" -Action {action}'
        # Formato Touch Portal: Run PowerShell Script (run visivel = 2)
        return [
            {
                "kIEn": True,
                "KEY_TYPE": "RUN_POWERSHELL_SCRIPT_ACTION",
                "KEY_POWERSHELL": self.plugin_script,
                "KEY_POWERSHELL_ARGS": f'-NoProfile -ExecutionPolicy Bypass -Action {action}',
                "KEY_POWERSHELL_RUNTYPE": 2,
            }
        ]

    def _btn(
        self,
        title: str,
        actions: list[dict],
        *,
        rows: int = 1,
        cols: int = 1,
        bg: tuple[int, int, int] = COLOR_BTN,
        row: int = 0,
        col: int = 0,
    ) -> PlacedButton:
        return PlacedButton(row, col, rows, cols, title, actions, bg)

    def _page(self, key: str, title: str, banner: str, rows: int, cols: int) -> PageSpec:
        spec = PageSpec(key=key, title=title, banner=banner, rows=rows, cols=cols)
        self.page_specs.append(spec)
        return spec

    def build_pages(self) -> list[str]:
        home = self._page("home", "ACOS Home", "AI-Commerce Home", 6, 4)
        prod = self._page("prod", "ACOS Producao", "AI-Commerce Producao", 7, 4)
        pipe = self._page("pipe", "ACOS Pipeline", "AI-Commerce Pipeline", 6, 4)
        git = self._page("git", "ACOS Git", "AI-Commerce Git", 5, 4)
        cloud = self._page("cloud", "ACOS Nuvem", "AI-Commerce Nuvem", 6, 4)

        builders = {
            spec.key: PageBuilder(spec)
            for spec in self.page_specs
        }
        for key, builder in builders.items():
            self.page_paths[key] = builder.path

        home.buttons = [
            self._btn("🧠\nCursor", self._run_ps("open-cursor"), cols=2, bg=COLOR_BTN_ACCENT),
            self._btn("📝\nVS Code", self._run_ps("open-vscode"), cols=2, col=2),
            self._btn("💻\nTerminal", self._run_ps("open-terminal"), row=1),
            self._btn("📁\nExplorer", self._run_ps("open-explorer"), row=1, col=2),
            self._btn("🌐\nFirefox", self._run_ps("open-firefox"), row=2),
            self._btn("🐳\nDocker", self._run_ps("open-docker"), row=2, col=2),
            self._btn("▶\nProducao", [self._goto("prod")], row=3, cols=4, bg=COLOR_BTN_ACCENT),
            self._btn("☁\nNuvem", [self._goto("cloud")], row=4, cols=2),
            self._btn("📤\nGit", [self._goto("git")], row=4, col=2, cols=2),
        ]

        prod.buttons = [
            self._btn("🚀\nPipeline IA", self._run_ps("pipeline-ia"), rows=2, cols=4, bg=COLOR_BTN_ACCENT),
            self._btn("🎯\nPipeline Tema", self._run_ps("pipeline-tema"), row=2, cols=4, bg=COLOR_BTN_ACCENT),
            self._btn("🎥\nUltimo video", self._run_ps("last-video"), row=3, cols=4),
            self._btn("📂\nOutputs", self._run_ps("outputs"), row=4, cols=2),
            self._btn("📤\nGit", [self._goto("git")], row=4, col=2, cols=2),
            self._btn("🐳\nDocker", self._run_ps("open-docker"), row=5),
            self._btn("💻\nTerminal", self._run_ps("open-terminal"), row=5, col=2, cols=2),
            self._btn("🏠\nHome", [self._goto("home")], row=6, cols=4),
        ]

        pipe.buttons = [
            self._btn("🚀 Pipeline IA", self._run_ps("pipeline-ia"), cols=4, bg=COLOR_BTN_ACCENT),
            self._btn("🎯 Pipeline Tema", self._run_ps("pipeline-tema"), row=1, cols=4, bg=COLOR_BTN_ACCENT),
            self._btn("🔄 Rerun", self._run_ps("pipeline-rerun"), row=2, cols=2),
            self._btn("🖥 Local", self._run_ps("pipeline-local"), row=2, col=2, cols=2),
            self._btn("📊 Logs", self._run_ps("logs"), row=3, cols=2),
            self._btn("🔌 API", self._run_ps("restart-api"), row=3, col=2, cols=2),
            self._btn("◀ Producao", [self._goto("prod")], row=4, cols=4),
        ]

        git.buttons = [
            self._btn("✅ Commit\nadd + status", self._run_ps("git-commit"), rows=2, cols=4, bg=COLOR_BTN_GIT),
            self._btn("⬆ Push", self._run_ps("git-push"), row=2, rows=2, cols=4, bg=COLOR_BTN_GIT),
            self._btn("📋 Status", self._run_ps("git-status"), row=4, cols=2),
            self._btn("◀ Voltar", [self._goto("prod")], row=4, col=2, cols=2),
        ]

        cloud.buttons = [
            self._btn("🚂 Railway", self._run_ps("open-railway"), cols=2, bg=COLOR_BTN_ACCENT),
            self._btn("▶ YT Studio", self._run_ps("open-youtube-studio"), cols=2, col=2, bg=COLOR_BTN_ACCENT),
            self._btn("🔌 Reiniciar API", self._run_ps("restart-api"), row=1, cols=2),
            self._btn("📂 Projeto", self._run_ps("open-project"), row=1, col=2, cols=2),
            self._btn("🧹 Limpar cache", self._run_ps("clear-cache"), row=2, cols=4, bg=COLOR_BTN_DANGER),
            self._btn("🏠 Home", [self._goto("home")], row=3, cols=4),
        ]

        return [builders[spec.key].render() for spec in self.page_specs]

    def write_pack(self, output: Path) -> None:
        pages = self.build_pages()
        data = {"pages": pages, "flows": [], "values": []}
        output.parent.mkdir(parents=True, exist_ok=True)

        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("version.json", json.dumps({"version": 2}, separators=(",", ":")))
            zf.writestr("data.json", payload)


def default_installed_plugin_script() -> str:
    return str(
        Path.home()
        / "AppData"
        / "Roaming"
        / "TouchPortal"
        / "plugins"
        / "AI-Commerce-OS"
        / "aicommerce.ps1"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera pacote Touch Portal (.tpz)")
    parser.add_argument(
        "--project-root",
        default=r"C:\Projetos\AI-Commerce-OS",
        help="Caminho do clone (usado apenas para mensagens)",
    )
    parser.add_argument(
        "--use-installed-plugin-path",
        action="store_true",
        help="Referencia aicommerce.ps1 em %%AppData%%\\TouchPortal\\plugins\\",
    )
    args = parser.parse_args()

    script_path = (
        default_installed_plugin_script()
        if args.use_installed_plugin_path
        else str(Path(args.project_root) / "infra" / "touchportal" / "aicommerce.ps1")
    )

    builder = PackBuilder(script_path)
    tpz = OUT_DIR / "AI-Commerce-OS-Panels.tpz"
    tpz2 = OUT_DIR / "AI-Commerce-OS-Panels.tpz2"
    builder.write_pack(tpz)
    builder.write_pack(tpz2)

    print(f"\n✅ Pacote gerado: {tpz}")
    print(f"   Alias: {tpz2}")
    print(f"   Script: {script_path}")
    print("\nImporte o arquivo .tpz (NAO de clique duplo).")
    print("Touch Portal → Pages → engrenagem → Import page → Desktop\\AI-Commerce-OS-Panels.tpz\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
