"""On-disk pipeline state: tracks the current phase, slug, and creation-phase snapshot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


STATE_FILENAME = ".pipeline-state.json"


class PipelineState(TypedDict, total=False):
    """On-disk representation of pipeline progress within a planning directory."""

    phase: str
    slug: str | None
    snapshot: list[str]
    updated_at: str


def state_path(planning_dir: Path) -> Path:
    """Return the absolute path of the pipeline state file."""
    return planning_dir / STATE_FILENAME


def read_state(planning_dir: Path) -> PipelineState | None:
    """Load pipeline state from disk, or return None if none has been written."""
    path = state_path(planning_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(planning_dir: Path, state: PipelineState) -> None:
    """Atomically write pipeline state with a refreshed `updated_at`."""
    path = state_path(planning_dir)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def clear_state(planning_dir: Path) -> None:
    """Remove the pipeline state file if present."""
    state_path(planning_dir).unlink(missing_ok=True)
