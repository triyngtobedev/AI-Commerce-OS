#!/usr/bin/env python3
"""
Gera e implanta pages Touch Portal para AI-Commerce-OS.

Saida:
  touchportal/dist/AI-Commerce-OS-Panels.tpz  (import manual)
  touchportal/dist/pages/*.tml                  (deploy direto)

Uso:
    python touchportal/build/build_pack.py
    python touchportal/build/build_pack.py --deploy "%APPDATA%\\TouchPortal\\pages"
    python touchportal/build/build_pack.py --project-root "D:\\Dev\\AI-Commerce-OS"
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ICONS_SRC = ROOT / "source" / "icons"

# IDs fixos — navegacao Go To Page depende de paths estaveis
PAGE_IDS = {
    "main": "1784557999999",
    "home": "1784558000001",
    "prod": "1784558000002",
    "pipe": "1784558000003",
    "git": "1784558000004",
    "cloud": "1784558000005",
}

ACTION_ICONS = {
    "open-cursor": "aico-cursor.png",
    "open-vscode": "aico-vscode.png",
    "open-project": "aico-project.png",
    "open-explorer": "aico-project.png",
    "pipeline-ia": "aico-pipeline.png",
    "pipeline-tema": "aico-pipeline.png",
    "pipeline-rerun": "aico-pipeline.png",
    "pipeline-local": "aico-pipeline.png",
    "open-docker": "aico-docker.png",
    "git-commit": "aico-github.png",
    "git-push": "aico-github.png",
    "git-status": "aico-github.png",
    "open-terminal": "aico-terminal.png",
    "open-railway": "aico-railway.png",
    "open-youtube-studio": "aico-railway.png",
    "last-video": "aico-pipeline.png",
    "outputs": "aico-project.png",
    "restart-api": "aico-terminal.png",
    "clear-cache": "aico-terminal.png",
    "logs": "aico-railway.png",
    "open-firefox": "",
}

COLOR_PAGE_BG = (12, 18, 32)
COLOR_BTN = (24, 36, 64)
COLOR_BTN_ACCENT = (255, 183, 3)
COLOR_BTN_GIT = (45, 106, 79)
COLOR_BTN_DANGER = (120, 45, 45)
COLOR_TEXT = (255, 255, 255)
GRID = 15


def rgb_to_tp(r: int, g: int, b: int, a: int = 255) -> int:
    value = (a << 24) | (r << 16) | (g << 8) | b
    return value - 0x100000000 if value >= 0x80000000 else value


def page_path(page_key: str) -> str:
    if page_key == "main":
        return "\\(main).tml"
    return f"\\{PAGE_IDS[page_key]}.tml"


def goto(page_key: str) -> dict:
    return {
        "kIEn": True,
        "KEY_PAGE_NAME": page_path(page_key),
        "KEY_TYPE": "GOTO_PAGE_ACTION",
    }


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
    action_key: str = ""


@dataclass
class PageSpec:
    key: str
    title: str
    banner: str
    rows: int
    cols: int
    buttons: list[PlacedButton] = field(default_factory=list)


class PackBuilder:
    def __init__(self, plugin_script: str):
        self.plugin_script = plugin_script.replace("/", "\\")
        self.specs: list[PageSpec] = []

    def _run_ps(self, action: str, *, visible: bool = False, pause: bool = False) -> list[dict]:
        args = f"-Action {action}"
        if pause:
            args += " -Pause"
        return [
            {
                "kIEn": True,
                "KEY_TYPE": "RUN_POWERSHELL_SCRIPT_ACTION",
                "KEY_POWERSHELL": self.plugin_script,
                "KEY_POWERSHELL_ARGS": args,
                "KEY_POWERSHELL_RUNTYPE": 2 if visible else 0,
            }
        ]

    def _run_bg(self, action: str) -> list[dict]:
        return self._run_ps(action, visible=False)

    def _run_win(self, action: str, *, pause: bool = True) -> list[dict]:
        return self._run_ps(action, visible=True, pause=pause)

    def _btn(
        self,
        title: str,
        actions: list[dict],
        *,
        action_key: str = "",
        row: int = 0,
        col: int = 0,
        rows: int = 1,
        cols: int = 1,
        bg: tuple[int, int, int] = COLOR_BTN,
    ) -> PlacedButton:
        icon = ACTION_ICONS.get(action_key, "") if action_key else ""
        return PlacedButton(row, col, rows, cols, title, actions, bg, icon, action_key)

    def _page(self, key: str, title: str, banner: str, rows: int, cols: int) -> PageSpec:
        spec = PageSpec(key, title, banner, rows, cols)
        self.specs.append(spec)
        return spec

    def build_specs(self) -> None:
        main = self._page("main", "(main)", "AI-Commerce Main", 2, 4)
        home = self._page("home", "ACOS Home", "AI-Commerce Home", 6, 4)
        prod = self._page("prod", "ACOS Producao", "AI-Commerce Producao", 6, 4)
        pipe = self._page("pipe", "ACOS Pipeline", "AI-Commerce Pipeline", 6, 4)
        git = self._page("git", "ACOS Git", "AI-Commerce Git", 5, 4)
        cloud = self._page("cloud", "ACOS Nuvem", "AI-Commerce Nuvem", 6, 4)

        main.buttons = [
            self._btn("Cursor", self._run_bg("open-cursor"), action_key="open-cursor", cols=1),
            self._btn("VS Code", self._run_bg("open-vscode"), action_key="open-vscode", col=1, cols=1),
            self._btn("Projeto", self._run_bg("open-project"), action_key="open-project", col=2, cols=1),
            self._btn("Pipeline", self._run_win("pipeline-ia", pause=False), action_key="pipeline-ia", col=3, cols=1, bg=COLOR_BTN_ACCENT),
            self._btn("Docker", self._run_bg("open-docker"), action_key="open-docker", row=1, cols=1),
            self._btn("Git Push", self._run_win("git-push", pause=False), action_key="git-push", row=1, col=1, cols=1, bg=COLOR_BTN_GIT),
            self._btn("Terminal", self._run_win("open-terminal", pause=False), action_key="open-terminal", row=1, col=2, cols=1),
            self._btn("Railway", self._run_bg("open-railway"), action_key="open-railway", row=1, col=3, cols=1, bg=COLOR_BTN_ACCENT),
        ]

        home.buttons = [
            self._btn("Cursor", self._run_bg("open-cursor"), action_key="open-cursor", cols=2, bg=COLOR_BTN_ACCENT),
            self._btn("VS Code", self._run_bg("open-vscode"), action_key="open-vscode", cols=2, col=2),
            self._btn("Terminal", self._run_win("open-terminal", pause=False), action_key="open-terminal", row=1),
            self._btn("Explorer", self._run_bg("open-explorer"), action_key="open-explorer", row=1, col=2),
            self._btn("Firefox", self._run_bg("open-firefox"), action_key="open-firefox", row=2),
            self._btn("Docker", self._run_bg("open-docker"), action_key="open-docker", row=2, col=2),
            self._btn("Producao", [goto("prod")], row=3, cols=4, bg=COLOR_BTN_ACCENT),
            self._btn("Nuvem", [goto("cloud")], row=4, cols=2),
            self._btn("Git", [goto("git")], row=4, col=2, cols=2, bg=COLOR_BTN_GIT),
        ]

        prod.buttons = [
            self._btn("Pipeline IA", self._run_win("pipeline-ia"), action_key="pipeline-ia", cols=2, bg=COLOR_BTN_ACCENT),
            self._btn("Ultimo video", self._run_bg("last-video"), action_key="last-video", cols=2, col=2),
            self._btn("Outputs", self._run_bg("outputs"), action_key="outputs", row=1, cols=2),
            self._btn("Git", [goto("git")], row=1, col=2, cols=2, bg=COLOR_BTN_GIT),
            self._btn("Docker", self._run_bg("open-docker"), action_key="open-docker", row=2, cols=2),
            self._btn("Terminal", self._run_win("open-terminal", pause=False), action_key="open-terminal", row=2, col=2, cols=2),
            self._btn("Home", [goto("home")], row=3, cols=4),
        ]

        pipe.buttons = [
            self._btn("Pipeline IA", self._run_win("pipeline-ia"), action_key="pipeline-ia", cols=2, bg=COLOR_BTN_ACCENT),
            self._btn("Rerun", self._run_win("pipeline-rerun"), action_key="pipeline-rerun", cols=2, col=2),
            self._btn("Local", self._run_win("pipeline-local"), action_key="pipeline-local", row=1, col=2, cols=2),
            self._btn("Logs", self._run_bg("logs"), action_key="logs", row=2, cols=2),
            self._btn("API", self._run_win("restart-api", pause=False), action_key="restart-api", row=2, col=2, cols=2),
            self._btn("Voltar", [goto("prod")], row=3, cols=4),
        ]

        git.buttons = [
            self._btn("Commit", self._run_win("git-commit"), action_key="git-commit", cols=2, bg=COLOR_BTN_GIT),
            self._btn("Push", self._run_win("git-push"), action_key="git-push", cols=2, col=2, bg=COLOR_BTN_GIT),
            self._btn("Status", self._run_win("git-status", pause=False), action_key="git-status", row=1, cols=2),
            self._btn("Voltar", [goto("prod")], row=1, col=2, cols=2),
        ]

        cloud.buttons = [
            self._btn("Railway", self._run_bg("open-railway"), action_key="open-railway", cols=2, bg=COLOR_BTN_ACCENT),
            self._btn("YT Studio", self._run_bg("open-youtube-studio"), action_key="open-youtube-studio", cols=2, col=2, bg=COLOR_BTN_ACCENT),
            self._btn("Reiniciar API", self._run_win("restart-api", pause=False), action_key="restart-api", row=1, cols=2),
            self._btn("Projeto", self._run_bg("open-project"), action_key="open-project", row=1, col=2, cols=2),
            self._btn("Limpar cache", self._run_win("clear-cache", pause=False), action_key="clear-cache", row=2, cols=4, bg=COLOR_BTN_DANGER),
            self._btn("Home", [goto("home")], row=3, cols=4),
        ]

    def render_page(self, spec: PageSpec) -> str:
        matrix: list[list[dict | None]] = [[None] * GRID for _ in range(GRID)]

        for btn in spec.buttons:
            bg = rgb_to_tp(*btn.bg)
            text = rgb_to_tp(*COLOR_TEXT)
            matrix[btn.row][btn.col] = {
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
                "kSCC": text,
                "kSCHRC": False,
                "THO": 4,
                "id": f"u{spec.key}{btn.row}{btn.col}",
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
                "TC": text,
                "kSVP": 0,
                "kSTP": 0,
                "kSVAC": text,
                "TO": 4,
                "TP": 2,
                "inB": False,
                "kSD": 0,
                "kSCTM": 0,
                "TS": text,
                "inC": 0,
                "ROWS": btn.rows,
            }

        page = {
            "kATO": "",
            "BG": rgb_to_tp(*COLOR_PAGE_BG),
            "MAX": False,
            "BGI": "",
            "kPL": 0,
            "kGB": True,
            "GUid": -1,
            "KEY_ID": PAGE_IDS[spec.key],
            "kATY": 0,
            "BUTTONS": matrix,
            "KEY_COLUMNS": spec.cols,
            "kFM": 16 if spec.key == "main" else 0,
            "kBN": spec.banner,
            "VERSION": 2,
            "kENA": True,
            "GUdata": "",
            "KEY_TITLE": spec.title,
            "KEY_ROWS": spec.rows,
            "BTN_MARGIN": 8 if spec.key == "main" else 4,
            "PO": 1 if spec.key == "main" else 0,
        }
        if spec.key == "main":
            page["KEY_TITLE"] = "(main)"
        return json.dumps(page, ensure_ascii=False, separators=(",", ":"))

    def filename_for(self, spec: PageSpec) -> str:
        if spec.key == "main":
            return "(main).tml"
        return f"{PAGE_IDS[spec.key]}.tml"

    def write_tpz(self, output: Path) -> None:
        pages = [self.render_page(s) for s in self.specs]
        payload = json.dumps({"pages": pages, "flows": [], "values": []}, ensure_ascii=False, separators=(",", ":"))
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("version.json", json.dumps({"version": 2}, separators=(",", ":")))
            zf.writestr("data.json", payload)
            for png in ICONS_SRC.glob("*.png"):
                zf.write(png, f"icons/{png.name}")

    def deploy_pages(self, dest: Path) -> list[str]:
        dest.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        for spec in self.specs:
            fname = self.filename_for(spec)
            path = dest / fname
            content = self.render_page(spec)
            path.write_bytes(content.encode("utf-8"))
            written.append(str(path))
        return written


def default_plugin_script() -> str:
    return str(Path.home() / "AppData/Roaming/TouchPortal/plugins/AI-Commerce-OS/aicommerce.ps1")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera/deploy Touch Portal pages AI-Commerce-OS")
    parser.add_argument("--project-root", default=r"C:\Projetos\AI-Commerce-OS")
    parser.add_argument("--plugin-script", default="")
    parser.add_argument("--deploy", default="", help="Pasta pages do Touch Portal (%APPDATA%\\TouchPortal\\pages)")
    args = parser.parse_args()

    script = args.plugin_script or default_plugin_script()
    builder = PackBuilder(script)
    builder.build_specs()

    tpz = DIST / "AI-Commerce-OS-Panels.tpz"
    builder.write_tpz(tpz)
    print(f"TPZ: {tpz}")

    pages_dir = DIST / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    for spec in builder.specs:
        out = pages_dir / builder.filename_for(spec)
        out.write_bytes(builder.render_page(spec).encode("utf-8"))
        print(f"TML: {out}")

    if args.deploy:
        deployed = builder.deploy_pages(Path(args.deploy))
        print(f"Deploy: {len(deployed)} pages em {args.deploy}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
