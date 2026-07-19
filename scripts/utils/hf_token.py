"""Hugging Face token — accepts HF_API_TOKEN or HF_TOKEN."""

from __future__ import annotations

import os


def get_hf_token() -> str:
    """Return HF token from HF_API_TOKEN or HF_TOKEN, whichever is set."""
    return (os.getenv("HF_API_TOKEN") or os.getenv("HF_TOKEN") or "").strip()


def hf_token_configured() -> bool:
    """True if either HF_API_TOKEN or HF_TOKEN is present."""
    return bool(get_hf_token())
