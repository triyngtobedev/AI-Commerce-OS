"""Testes do Quality Gate."""

import json
import tempfile
from pathlib import Path

from scripts.core.production.quality_gate import run_quality_gate
from scripts.core.asset_rights_ledger import AssetRightsLedger


def _make_media_search(folder: Path, scenes: list) -> None:
    assets = folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "media_search.json").write_text(
        json.dumps({"scenes": scenes, "version": 4}),
        encoding="utf-8",
    )


def test_quality_gate_approves_good_footage():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _make_media_search(folder, [
            {"scene": 1, "saved": True, "media_type": "video", "provedor": "pexels", "quality_score": 0.8, "width": 1920, "height": 1080},
            {"scene": 2, "saved": True, "media_type": "video", "provedor": "wikimedia", "quality_score": 0.75, "width": 1920, "height": 1080},
            {"scene": 3, "saved": True, "media_type": "image", "provedor": "pixabay", "quality_score": 0.7, "width": 1920, "height": 1080},
        ])
        ledger = AssetRightsLedger(folder)
        for i in range(1, 4):
            ledger.register_asset(source="pexels", provider="pexels", license_text="Pexels License", scene_id=i, media_type="video")

        result = {"cenas": {"cenas": [{"duration_seconds": 60}] * 3}}
        report = run_quality_gate(folder, result, block_on_failure=False, ledger=ledger)

        assert report.approved is True
        assert (folder / "quality_report.json").exists()


def test_quality_gate_blocks_excess_t2v():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        scenes = [
            {"scene": i, "saved": True, "media_type": "ai_video", "provedor": "replicate", "quality_score": 0.5}
            for i in range(1, 4)
        ]
        _make_media_search(folder, scenes)
        ledger = AssetRightsLedger(folder)

        report = run_quality_gate(
            folder, {"cenas": {"cenas": []}},
            block_on_failure=False, ledger=ledger,
        )
        assert report.blocked is True
        assert any("T2V" in r for r in report.block_reasons)
