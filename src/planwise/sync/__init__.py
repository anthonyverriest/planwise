"""Sync: pluggable supervised-operator framework for multi-tool pipelines."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()
