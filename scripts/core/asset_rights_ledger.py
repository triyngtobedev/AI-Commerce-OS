"""
Asset Rights Ledger — registro persistente de direitos de mídia por vídeo.

Nenhum asset entra no render final sem licença avaliada.
Exporta asset_rights_report.json e credits.txt quando necessário.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Licenças consideradas seguras para uso comercial no YouTube
_SAFE_LICENSES = {
    "cc0",
    "public domain",
    "publicdomain",
    "pd",
    "pexels license",
    "pixabay license",
    "mixkit license",
    "coverr license",
    "nasa",
    "us government work",
    "cc-by",
    "cc by",
    "creative commons attribution",
    "cc-by-sa",
    "cc by-sa",
    "creative commons attribution-sharealike",
    "cc-by-2.0",
    "cc-by-3.0",
    "cc-by-4.0",
    "cc-by-sa-2.0",
    "cc-by-sa-3.0",
    "cc-by-sa-4.0",
    "mit",
    "unrestricted",
}

_UNSAFE_LICENSES = {
    "all rights reserved",
    "copyright",
    "editorial use only",
    "non-commercial",
    "nc",
    "nd",
    "no derivatives",
    "unknown",
    "unclear",
    "watermarked",
}

_PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "wikimedia": {
        "license": "varies (Commons)",
        "commercial_use_allowed": True,
        "attribution_required": True,
        "license_safety_score": 0.85,
    },
    "pexels": {
        "license": "Pexels License",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.95,
    },
    "pixabay": {
        "license": "Pixabay License",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.95,
    },
    "internet_archive": {
        "license": "Public Domain / varies",
        "commercial_use_allowed": True,
        "attribution_required": True,
        "license_safety_score": 0.80,
    },
    "nasa": {
        "license": "NASA Media Guidelines",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 1.0,
    },
    "coverr": {
        "license": "Coverr License",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.95,
    },
    "mixkit": {
        "license": "Mixkit License",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.95,
    },
    "openverse": {
        "license": "varies (Openverse)",
        "commercial_use_allowed": True,
        "attribution_required": True,
        "license_safety_score": 0.75,
    },
    "pollinations": {
        "license": "Pollinations generated",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.70,
    },
    "huggingface": {
        "license": "AI generated",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.65,
    },
    "replicate": {
        "license": "AI generated (T2V)",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.60,
    },
    "n8n": {
        "license": "AI generated (T2V)",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.60,
    },
    "generated": {
        "license": "Editorial composite",
        "commercial_use_allowed": True,
        "attribution_required": False,
        "license_safety_score": 0.90,
    },
}


@dataclass
class AssetRecord:
    asset_id: str
    source: str
    source_url: str = ""
    download_url: str = ""
    creator: str = ""
    license: str = "unknown"
    commercial_use_allowed: bool = False
    attribution_required: bool = False
    attribution_text: str = ""
    media_type: str = "unknown"
    duration: float = 0.0
    resolution: str = ""
    topic_relevance_score: float = 0.0
    visual_quality_score: float = 0.0
    license_safety_score: float = 0.0
    used_in_scene_ids: list[int] = field(default_factory=list)
    downloaded_at: str = ""
    checksum: str = ""
    local_path: str = ""
    is_safe: bool = False
    unsafe_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_license(license_text: str) -> str:
    return " ".join(str(license_text or "unknown").lower().split())


def evaluate_license(
    license_text: str,
    *,
    provider: str = "",
    has_watermark: bool = False,
) -> dict[str, Any]:
    """Avalia licença e retorna flags de segurança."""

    normalized = _normalize_license(license_text)
    provider_key = (provider or "").lower().split(":")[0]
    defaults = _PROVIDER_DEFAULTS.get(provider_key, {})

    if has_watermark:
        return {
            "license": license_text or "watermarked",
            "commercial_use_allowed": False,
            "attribution_required": True,
            "license_safety_score": 0.0,
            "is_safe": False,
            "unsafe_reason": "watermark detected",
        }

    for unsafe in _UNSAFE_LICENSES:
        if unsafe in normalized:
            return {
                "license": license_text or unsafe,
                "commercial_use_allowed": False,
                "attribution_required": True,
                "license_safety_score": 0.0,
                "is_safe": False,
                "unsafe_reason": f"license flagged: {unsafe}",
            }

    is_safe = False
    safety_score = defaults.get("license_safety_score", 0.5)

    for safe in _SAFE_LICENSES:
        if safe in normalized:
            is_safe = True
            safety_score = max(safety_score, 0.85)
            break

    if not is_safe and defaults:
        is_safe = bool(defaults.get("commercial_use_allowed"))
        safety_score = float(defaults.get("license_safety_score", safety_score))

    if normalized in ("unknown", "") and defaults:
        is_safe = bool(defaults.get("commercial_use_allowed"))
        license_text = defaults.get("license", "unknown")

    commercial = defaults.get("commercial_use_allowed", is_safe) if is_safe else False
    attribution = defaults.get("attribution_required", False)

    if "cc-by" in normalized or "attribution" in normalized:
        attribution = True

    return {
        "license": license_text or defaults.get("license", "unknown"),
        "commercial_use_allowed": commercial,
        "attribution_required": attribution,
        "license_safety_score": round(safety_score, 3),
        "is_safe": is_safe,
        "unsafe_reason": "" if is_safe else "license not verified",
    }


def compute_file_checksum(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AssetRightsLedger:
    """Registro local persistente de assets por vídeo."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.ledger_path = self.output_dir / "assets" / "asset_rights_ledger.json"
        self._records: dict[str, AssetRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.ledger_path.exists():
            return
        try:
            data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            for item in data.get("assets", []):
                record = AssetRecord(**{k: v for k, v in item.items() if k in AssetRecord.__dataclass_fields__})
                self._records[record.asset_id] = record
        except (json.JSONDecodeError, TypeError):
            pass

    def _save(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "assets": [r.to_dict() for r in self._records.values()],
        }
        self.ledger_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def register_asset(
        self,
        *,
        source: str,
        provider: str = "",
        source_url: str = "",
        download_url: str = "",
        creator: str = "",
        license_text: str = "",
        media_type: str = "unknown",
        duration: float = 0.0,
        width: int = 0,
        height: int = 0,
        topic_relevance_score: float = 0.0,
        visual_quality_score: float = 0.0,
        scene_id: int = 0,
        local_path: str | Path = "",
        item_id: Any = None,
        has_watermark: bool = False,
        credit: str = "",
    ) -> AssetRecord:
        """Registra ou atualiza um asset no ledger."""

        provider_key = (provider or source or "unknown").lower().split(":")[0]
        license_eval = evaluate_license(
            license_text or _PROVIDER_DEFAULTS.get(provider_key, {}).get("license", "unknown"),
            provider=provider_key,
            has_watermark=has_watermark,
        )

        path = Path(local_path) if local_path else None
        checksum = compute_file_checksum(path) if path and path.exists() else ""
        asset_id = checksum[:16] if checksum else f"{provider_key}-{item_id or scene_id}"

        resolution = f"{width}x{height}" if width and height else ""

        attribution_text = credit or creator
        if license_eval["attribution_required"] and creator and license_eval["license"]:
            attribution_text = f"{creator} — {license_eval['license']}"

        if asset_id in self._records:
            record = self._records[asset_id]
            if scene_id and scene_id not in record.used_in_scene_ids:
                record.used_in_scene_ids.append(scene_id)
            record.topic_relevance_score = max(record.topic_relevance_score, topic_relevance_score)
            record.visual_quality_score = max(record.visual_quality_score, visual_quality_score)
            self._save()
            return record

        record = AssetRecord(
            asset_id=asset_id,
            source=provider_key or source,
            source_url=source_url,
            download_url=download_url or source_url,
            creator=creator,
            license=license_eval["license"],
            commercial_use_allowed=license_eval["commercial_use_allowed"],
            attribution_required=license_eval["attribution_required"],
            attribution_text=attribution_text,
            media_type=media_type,
            duration=duration,
            resolution=resolution,
            topic_relevance_score=topic_relevance_score,
            visual_quality_score=visual_quality_score,
            license_safety_score=license_eval["license_safety_score"],
            used_in_scene_ids=[scene_id] if scene_id else [],
            downloaded_at=datetime.now(timezone.utc).isoformat(),
            checksum=checksum,
            local_path=str(path) if path else "",
            is_safe=license_eval["is_safe"],
            unsafe_reason=license_eval.get("unsafe_reason", ""),
        )
        self._records[asset_id] = record
        self._save()
        return record

    def get_unsafe_assets(self) -> list[AssetRecord]:
        return [r for r in self._records.values() if not r.is_safe]

    def all_safe(self) -> bool:
        return all(r.is_safe for r in self._records.values()) if self._records else True

    def export_report(self, export_folder: Optional[Path] = None) -> Path:
        """Exporta asset_rights_report.json e credits.txt se necessário."""

        folder = Path(export_folder) if export_folder else self.output_dir
        folder.mkdir(parents=True, exist_ok=True)

        records = list(self._records.values())
        unsafe = self.get_unsafe_assets()
        attribution_lines = [
            r.attribution_text
            for r in records
            if r.attribution_required and r.attribution_text
        ]

        report = {
            "total_assets": len(records),
            "safe_assets": len(records) - len(unsafe),
            "unsafe_assets": len(unsafe),
            "all_safe": self.all_safe(),
            "requires_credits": bool(attribution_lines),
            "assets": [r.to_dict() for r in records],
            "unsafe_details": [
                {"asset_id": r.asset_id, "reason": r.unsafe_reason, "source": r.source}
                for r in unsafe
            ],
        }

        report_path = folder / "asset_rights_report.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        if attribution_lines:
            credits_path = folder / "credits.txt"
            credits_path.write_text(
                "Créditos de mídia\n" + "=" * 40 + "\n\n" + "\n".join(sorted(set(attribution_lines))),
                encoding="utf-8",
            )

        return report_path
