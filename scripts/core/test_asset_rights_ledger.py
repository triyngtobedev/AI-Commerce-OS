"""Testes do Asset Rights Ledger."""

import json
import tempfile
from pathlib import Path

from scripts.core.asset_rights_ledger import (
    AssetRightsLedger,
    evaluate_license,
    compute_file_checksum,
)


def test_evaluate_license_pexels_safe():
    result = evaluate_license("Pexels License", provider="pexels")
    assert result["is_safe"] is True
    assert result["commercial_use_allowed"] is True


def test_evaluate_license_watermark_unsafe():
    result = evaluate_license("Pexels License", provider="pexels", has_watermark=True)
    assert result["is_safe"] is False
    assert "watermark" in result["unsafe_reason"]


def test_evaluate_license_editorial_only_unsafe():
    result = evaluate_license("Editorial use only")
    assert result["is_safe"] is False


def test_ledger_register_and_export():
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        ledger = AssetRightsLedger(output_dir)

        record = ledger.register_asset(
            source="pexels",
            provider="pexels",
            license_text="Pexels License",
            media_type="video",
            scene_id=1,
            width=1920,
            height=1080,
            topic_relevance_score=0.8,
        )
        assert record.is_safe is True

        report_path = ledger.export_report(output_dir)
        assert report_path.exists()

        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["all_safe"] is True
        assert data["total_assets"] == 1


def test_ledger_blocks_unsafe_asset():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = AssetRightsLedger(Path(tmp))
        record = ledger.register_asset(
            source="unknown",
            provider="unknown",
            license_text="All rights reserved",
            media_type="video",
            scene_id=1,
        )
        assert record.is_safe is False
        assert len(ledger.get_unsafe_assets()) == 1


def test_compute_checksum():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"test content")
        path = Path(f.name)

    checksum = compute_file_checksum(path)
    assert len(checksum) == 64
    path.unlink()
