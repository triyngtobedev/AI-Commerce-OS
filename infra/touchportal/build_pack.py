#!/usr/bin/env python3
"""
Gera o pacote importavel do Touch Portal para AI-Commerce-OS.

Saida:
  infra/touchportal/dist/AI-Commerce-OS-Panels.tpz2
  infra/touchportal/dist/icons/*.png

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
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "dist"
ICON_DIR = OUT_DIR / "icons"

# Tema escuro alinhado ao canal dark / marca Atlas
COLOR_PAGE_BG = (12, 18, 32)       # #0C1220
COLOR_BTN = (24, 36, 64)           # botao padrao
COLOR_BTN_ACCENT = (255, 183, 3)   # #FFB703
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


def _png_rgb(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    """PNG RGB minimal sem dependencias externas."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    raw = b"".join(
        b"\x00" + bytes([rgb[0], rgb[1], rgb[2]] * width)
        for _ in range(height)
    )
    compressed = zlib.compress(raw, 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


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
    auto_place: bool = False


class PageBuilder:
    def __init__(
        self,
        title: str,
        *,
        rows: int = 6,
        cols: int = 4,
        page_bg: tuple[int, int, int] = COLOR_PAGE_BG,
    ):
        self.title = title
        self.rows = rows
        self.cols = cols
        self.page_bg = page_bg
        self.key_id = str(int(time.time() * 1000))[-13:]
        self.buttons: list[PlacedButton] = []

    def add(self, button: PlacedButton) -> None:
        self.buttons.append(button)

    def _occupy(self, grid: list[list[bool]], btn: PlacedButton) -> None:
        for r in range(btn.row, btn.row + btn.rows):
            for c in range(btn.col, btn.col + btn.cols):
                if r < GRID_SIZE and c < GRID_SIZE:
                    grid[r][c] = True

    def _find_slot(self, grid: list[list[bool]], rows: int, cols: int) -> tuple[int, int]:
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if r + rows > GRID_SIZE or c + cols > GRID_SIZE:
                    continue
                ok = True
                for rr in range(r, r + rows):
                    for cc in range(c, c + cols):
                        if grid[rr][cc]:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    return r, c
        return 0, 0

    def _make_button(self, btn: PlacedButton) -> dict:
        bg = rgb_to_tp(*btn.bg)
        text_color = rgb_to_tp(*COLOR_TEXT)
        return {
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

    def render(self) -> str:
        grid = [[False] * GRID_SIZE for _ in range(GRID_SIZE)]
        matrix: list[list[dict | None]] = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]

        for btn in self.buttons:
            row, col = btn.row, btn.col
            if btn.auto_place:
                row, col = self._find_slot(grid, btn.rows, btn.cols)

            for rr in range(row, row + btn.rows):
                for cc in range(col, col + btn.cols):
                    if rr < GRID_SIZE and cc < GRID_SIZE:
                        grid[rr][cc] = True

            matrix[row][col] = self._make_button(
                PlacedButton(row, col, btn.rows, btn.cols, btn.title, btn.actions, btn.bg, btn.icon)
            )

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
            "KEY_COLUMNS": self.cols,
            "kFM": 0,
            "kBN": self.title,
            "VERSION": 1,
            "kENA": True,
            "GUdata": "",
            "KEY_TITLE": self.title,
            "KEY_ROWS": self.rows,
            "BTN_MARGIN": 4,
            "PO": 0,
        }
        return json.dumps(page, ensure_ascii=False, separators=(",", ":"))


class PackBuilder:
    def __init__(self, project_root: str, plugin_script: str):
        self.project_root = project_root.replace("/", "\\")
        self.plugin_script = plugin_script.replace("/", "\\")
        self.pages: list[str] = []
        self.icons: dict[str, bytes] = {}
        self.page_paths: dict[str, str] = {}

    def _icon(self, name: str, rgb: tuple[int, int, int]) -> str:
        filename = f"{name}.png"
        if filename not in self.icons:
            self.icons[filename] = _png_rgb(128, 128, rgb)
        return filename

    def _goto(self, page_title: str) -> dict:
        path = self.page_paths.get(page_title, "\\(main).tml")
        return {
            "KEY_PAGE_NAME": path,
            "kIEn": True,
            "KEY_TYPE": "GOTO_PAGE_ACTION",
        }

    def _open_url(self, url: str) -> dict:
        return {
            "kIEn": True,
            "KEY_URL": url,
            "KEY_TYPE": "OPEN_URL_ACTION",
        }

    def _run_ps(self, action: str, *, topic: str = "") -> list[dict]:
        args = f"-Action {action}"
        if topic:
            args += f' -Topic "{topic}"'
        cmd = (
            f'powershell.exe -NoProfile -ExecutionPolicy Bypass '
            f'-File "{self.plugin_script}" {args}'
        )
        # Formato usado pelo Touch Portal 4.x para Run Application
        return [
            {
                "kIEn": True,
                "KEY_TYPE": "START_APPLICATION_ACTION",
                "KEY_APPLICATION": "powershell.exe",
                "KEY_PARAMETERS": (
                    f'-NoProfile -ExecutionPolicy Bypass -File "{self.plugin_script}" {args}'
                ),
            }
        ]

    def _plugin_action(self, action_id: str) -> list[dict]:
        """Fallback via acao estatica do plugin (apos install.ps1)."""
        return [
            {
                "kIEn": True,
                "KEY_TYPE": "EXECUTE_PLUGIN_ACTION",
                "KEY_PLUGIN_ID": "com.triyn.aicommerceos",
                "KEY_ACTION_ID": action_id,
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
        icon: str = "",
        row: int = 0,
        col: int = 0,
    ) -> PlacedButton:
        return PlacedButton(row, col, rows, cols, title, actions, bg, icon)

    def build_pages(self) -> None:
        # --- Pagina 1: Home ---
        home = PageBuilder("🏠 Home", rows=6, cols=4)
        home_path = f"\\{home.key_id}.tml"
        self.page_paths["🏠 Home"] = home_path

        home.add(self._btn("🧠\nCursor", self._run_ps("open-cursor"), rows=1, cols=2, bg=COLOR_BTN_ACCENT, row=0, col=0))
        home.add(self._btn("📝\nVS Code", self._run_ps("open-vscode"), rows=1, cols=2, row=0, col=2))
        home.add(self._btn("💻\nTerminal", self._run_ps("open-terminal"), rows=1, cols=2, row=1, col=0))
        home.add(self._btn("📁\nExplorer", self._run_ps("open-explorer"), rows=1, cols=2, row=1, col=2))
        home.add(self._btn("🌐\nFirefox", self._run_ps("open-firefox"), rows=1, cols=2, row=2, col=0))
        home.add(self._btn("🐳\nDocker", self._run_ps("open-docker"), rows=1, cols=2, row=2, col=2))
        home.add(self._btn("▶\nProducao", [self._goto("🚀 Producao")], rows=1, cols=4, bg=COLOR_BTN_ACCENT, row=3, col=0))
        home.add(self._btn("☁\nNuvem", [self._goto("☁ Nuvem")], rows=1, cols=2, row=4, col=0))
        home.add(self._btn("📤\nGit", [self._goto("📤 Git")], rows=1, cols=2, row=4, col=2))
        self.pages.append(home.render())

        # --- Pagina 2: Producao (layout iPhone — botoes grandes) ---
        prod = PageBuilder("🚀 Producao", rows=7, cols=4)
        prod_path = f"\\{prod.key_id}.tml"
        self.page_paths["🚀 Producao"] = prod_path

        prod.add(self._btn("🚀\nPipeline IA", self._run_ps("pipeline-ia"), rows=2, cols=4, bg=COLOR_BTN_ACCENT, row=0, col=0))
        prod.add(self._btn("🎯\nPipeline Tema", self._plugin_action("acmd_pipeline_tema"), rows=1, cols=4, bg=COLOR_BTN_ACCENT, row=2, col=0))
        prod.add(self._btn("🎥\nUltimo video", self._run_ps("last-video"), rows=1, cols=4, row=3, col=0))
        prod.add(self._btn("📂\nOutputs", self._run_ps("outputs"), rows=1, cols=2, row=4, col=0))
        prod.add(self._btn("📤\nGit", [self._goto("📤 Git")], rows=1, cols=2, row=4, col=2))
        prod.add(self._btn("🐳\nDocker", self._run_ps("open-docker"), rows=1, cols=2, row=5, col=0))
        prod.add(self._btn("💻\nTerminal", self._run_ps("open-terminal"), rows=1, cols=2, row=5, col=2))
        prod.add(self._btn("🏠\nHome", [self._goto("🏠 Home")], rows=1, cols=4, row=6, col=0))
        self.pages.append(prod.render())

        # --- Pagina 3: Pipeline detalhado ---
        pipe = PageBuilder("🎬 Pipeline", rows=6, cols=4)
        pipe_path = f"\\{pipe.key_id}.tml"
        self.page_paths["🎬 Pipeline"] = pipe_path

        pipe.add(self._btn("🚀 Pipeline IA", self._run_ps("pipeline-ia"), rows=1, cols=4, bg=COLOR_BTN_ACCENT, row=0, col=0))
        pipe.add(self._btn("🎯 Pipeline Tema", self._plugin_action("acmd_pipeline_tema"), rows=1, cols=4, bg=COLOR_BTN_ACCENT, row=1, col=0))
        pipe.add(self._btn("🔄 Rerun", self._run_ps("pipeline-rerun"), rows=1, cols=2, row=2, col=0))
        pipe.add(self._btn("🖥 Local", self._run_ps("pipeline-local"), rows=1, cols=2, row=2, col=2))
        pipe.add(self._btn("📊 Logs", self._run_ps("logs"), rows=1, cols=2, row=3, col=0))
        pipe.add(self._btn("🔌 API", self._run_ps("restart-api"), rows=1, cols=2, row=3, col=2))
        pipe.add(self._btn("◀ Producao", [self._goto("🚀 Producao")], rows=1, cols=4, row=4, col=0))
        self.pages.append(pipe.render())

        # --- Pagina 4: Git (dois botoes separados) ---
        git = PageBuilder("📤 Git", rows=5, cols=4)
        git_path = f"\\{git.key_id}.tml"
        self.page_paths["📤 Git"] = git_path

        git.add(self._btn("✅ Commit\nadd + status", self._run_ps("git-commit"), rows=2, cols=4, bg=COLOR_BTN_GIT, row=0, col=0))
        git.add(self._btn("⬆ Push", self._run_ps("git-push"), rows=2, cols=4, bg=COLOR_BTN_GIT, row=2, col=0))
        git.add(self._btn("📋 Status", self._run_ps("git-status"), rows=1, cols=2, row=4, col=0))
        git.add(self._btn("◀ Voltar", [self._goto("🚀 Producao")], rows=1, cols=2, row=4, col=2))
        self.pages.append(git.render())

        # --- Pagina 5: Nuvem / ferramentas ---
        cloud = PageBuilder("☁ Nuvem", rows=6, cols=4)
        cloud_path = f"\\{cloud.key_id}.tml"
        self.page_paths["☁ Nuvem"] = cloud_path

        cloud.add(self._btn("🚂 Railway", self._run_ps("open-railway"), rows=1, cols=2, bg=COLOR_BTN_ACCENT, row=0, col=0))
        cloud.add(self._btn("▶ YT Studio", self._run_ps("open-youtube-studio"), rows=1, cols=2, bg=COLOR_BTN_ACCENT, row=0, col=2))
        cloud.add(self._btn("🔌 Reiniciar API", self._run_ps("restart-api"), rows=1, cols=2, row=1, col=0))
        cloud.add(self._btn("📂 Projeto", self._run_ps("open-project"), rows=1, cols=2, row=1, col=2))
        cloud.add(self._btn("🧹 Limpar cache", self._run_ps("clear-cache"), rows=1, cols=4, bg=COLOR_BTN_DANGER, row=2, col=0))
        cloud.add(self._btn("🏠 Home", [self._goto("🏠 Home")], rows=1, cols=4, row=3, col=0))
        self.pages.append(cloud.render())

    def write_tpz2(self, output: Path) -> None:
        data = {"pages": self.pages, "flows": [], "values": []}
        output.parent.mkdir(parents=True, exist_ok=True)
        ICON_DIR.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("version.json", json.dumps({"version": 2}))
            zf.writestr("data.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            for name, blob in self.icons.items():
                zf.writestr(f"img/{name}", blob)


def default_plugin_script(project_root: str) -> str:
    return str(
        Path(project_root) / "infra" / "touchportal" / "aicommerce.ps1"
    )


def default_installed_plugin_script() -> str:
    appdata = Path.home() / "AppData" / "Roaming" / "TouchPortal" / "plugins" / "AI-Commerce-OS" / "aicommerce.ps1"
    return str(appdata)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera pacote Touch Portal (.tpz2)")
    parser.add_argument(
        "--project-root",
        default=r"C:\Projetos\AI-Commerce-OS",
        help="Caminho do clone AI-Commerce-OS no Windows",
    )
    parser.add_argument(
        "--use-installed-plugin-path",
        action="store_true",
        help="Usa %AppData%\\TouchPortal\\plugins\\AI-Commerce-OS\\aicommerce.ps1 nos botoes",
    )
    args = parser.parse_args()

    script_path = (
        default_installed_plugin_script()
        if args.use_installed_plugin_path
        else default_plugin_script(args.project_root)
    )

    builder = PackBuilder(args.project_root, script_path)
    builder.build_pages()

    output = OUT_DIR / "AI-Commerce-OS-Panels.tpz2"
    builder.write_tpz2(output)

    print(f"\n✅ Pacote gerado: {output}")
    print(f"   Script referenciado: {script_path}")
    print("\nImporte no Touch Portal: Pages → engrenagem → Import page\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
