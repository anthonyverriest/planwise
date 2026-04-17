"""Sync state persistence: read/write planwise/.sync-state.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

from filelock import FileLock

from planwise.sync import now_iso as _now_iso
from planwise.sync.errors import StateCorruptedError
from planwise.sync.types import MAX_STORED_OUTPUT_LINES, StepResult, SyncState


def _truncate_output(text: str) -> str:
    """Keep only the last N lines of output for storage."""
    lines = text.splitlines()
    if len(lines) <= MAX_STORED_OUTPUT_LINES:
        return text
    return "\n".join(lines[-MAX_STORED_OUTPUT_LINES:])


def _state_path(planning_dir: Path) -> Path:
    """Resolve the state file path."""
    return planning_dir / ".sync-state.json"


def _lock_path(planning_dir: Path) -> Path:
    """Resolve the lock file path (reuse planwise's existing lock)."""
    return planning_dir / ".lock"


def create_state(pipeline_name: str, step_names: list[str]) -> SyncState:
    """Create a fresh sync state for a pipeline run."""
    now = _now_iso()
    steps: list[StepResult] = [
        StepResult(step_name=name, status="pending") for name in step_names
    ]
    return SyncState(
        pipeline_name=pipeline_name,
        started_at=now,
        updated_at=now,
        current_step=-1,
        steps=steps,
        completed=False,
    )


def read_state(planning_dir: Path) -> SyncState | None:
    """Read sync state from disk, returning None if no state file exists."""
    path = _state_path(planning_dir)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        raw = json.loads(text)
    except (json.JSONDecodeError, OSError) as exc:
        raise StateCorruptedError(f"Cannot read state file {path}: {exc}") from exc

    required = {"pipeline_name", "started_at", "updated_at", "current_step", "steps", "completed"}
    missing = required - raw.keys()
    if missing:
        raise StateCorruptedError(
            f"State file missing fields: {', '.join(sorted(missing))}"
        )
    return raw


def write_state(planning_dir: Path, sync_state: SyncState) -> None:
    """Atomically write sync state to disk with file locking."""
    sync_state["updated_at"] = _now_iso()

    for step in sync_state["steps"]:
        if "stdout" in step:
            step["stdout"] = _truncate_output(step["stdout"])
        if "stderr" in step:
            step["stderr"] = _truncate_output(step["stderr"])

    path = _state_path(planning_dir)
    lock = FileLock(_lock_path(planning_dir))
    with lock:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(sync_state, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)


def update_step(sync_state: SyncState, step_name: str, updates: StepResult) -> None:
    """Update a specific step's result in the state, in place."""
    for step in sync_state["steps"]:
        if step.get("step_name") == step_name:
            step.update(updates)
            return
    assert False, f"Step '{step_name}' not found in state"


def delete_state(planning_dir: Path) -> bool:
    """Delete the state file. Returns True if a file was removed."""
    path = _state_path(planning_dir)
    if path.is_file():
        path.unlink()
        return True
    return False
