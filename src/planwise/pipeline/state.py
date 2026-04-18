"""On-disk pipeline state: per-slug files tracking the current workflow phase.

State is keyed by issue slug so parallel pipelines (e.g., two `/implement`
sessions on different features) never collide. Creation phases (plan/brief/bug)
write no state — `/next` resolves their candidates from the issue store.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


STATE_DIRNAME = ".pipelines"


class SlugState(TypedDict, total=False):
    """On-disk record of a slug-consuming pipeline's current phase."""

    phase: str
    updated_at: str


def _state_dir(planning_dir: Path) -> Path:
    """Return the directory holding per-slug pipeline state files."""
    return planning_dir / STATE_DIRNAME


def _slug_path(planning_dir: Path, slug: str) -> Path:
    """Return the absolute path of the state file for a given slug."""
    return _state_dir(planning_dir) / f"{slug}.json"


def read_slug_state(planning_dir: Path, slug: str) -> SlugState | None:
    """Load the slug's pipeline state, or None if none has been written."""
    path = _slug_path(planning_dir, slug)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_slug_state(planning_dir: Path, slug: str, state: SlugState) -> None:
    """Atomically write the slug's pipeline state with a refreshed `updated_at`."""
    path = _slug_path(planning_dir, slug)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def delete_slug_state(planning_dir: Path, slug: str) -> None:
    """Remove the slug's pipeline state file if present."""
    _slug_path(planning_dir, slug).unlink(missing_ok=True)


def list_slug_states(planning_dir: Path) -> list[tuple[str, SlugState]]:
    """Return [(slug, state), ...] for every slug with an on-disk pipeline record."""
    state_dir = _state_dir(planning_dir)
    if not state_dir.is_dir():
        return []
    results: list[tuple[str, SlugState]] = []
    for path in state_dir.glob("*.json"):
        if path.name.startswith("."):
            continue
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        results.append((path.stem, state))
    return results
