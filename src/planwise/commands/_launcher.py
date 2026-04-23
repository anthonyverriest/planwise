"""Shared jj workspace setup for agent-launcher commands (`pw claude`, `pw cursor`).

Each invocation creates a disposable jj workspace off `dev@origin`. Concurrent
invocations never collide on `@` because every workspace has its own working
copy while sharing the same `.jj/repo/` backend. Cleanup is manual once the
feature ships:

    jj workspace forget <name>
    rm -rf <path>
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click

TRUNK_REVSET = "dev@origin"
WORKSPACE_PREFIX = "wt-"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def main_repo_root() -> Path:
    """Return the main git working tree root.

    In colocated jj repos, jj workspaces are git worktrees. `git worktree list`
    always lists the main tree first, regardless of which workspace we are
    invoked from.
    """
    try:
        result = _run(["git", "worktree", "list"])
    except subprocess.CalledProcessError as exc:
        raise click.UsageError(
            f"`git worktree list` failed:\n{exc.stderr or exc.stdout}".rstrip()
        ) from exc
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise click.UsageError("Not inside a git repository.")
    return Path(lines[0].split()[0])


def new_workspace_name() -> str:
    """Generate a timestamped workspace name (UTC, millisecond precision)."""
    now = datetime.now(timezone.utc)
    return f"{WORKSPACE_PREFIX}{now.strftime('%Y%m%d-%H%M%S')}-{now.microsecond // 1000:03d}"


def workspace_path(main_root: Path, name: str) -> Path:
    """Compute the on-disk path for a named workspace."""
    return main_root.parent / f"{main_root.name}-{name}"


def fetch_trunk(main_root: Path) -> None:
    """Refresh `dev@origin` so the new workspace starts on current trunk."""
    try:
        _run(["jj", "--repository", str(main_root), "git", "fetch"])
    except subprocess.CalledProcessError as exc:
        raise click.UsageError(
            f"`jj git fetch` failed:\n{exc.stderr or exc.stdout}".rstrip()
        ) from exc


def create_workspace(main_root: Path, name: str, path: Path) -> None:
    """Materialize a new jj workspace rooted at `dev@origin`."""
    try:
        _run(
            [
                "jj",
                "--repository",
                str(main_root),
                "workspace",
                "add",
                str(path),
                "--name",
                name,
                "-r",
                TRUNK_REVSET,
            ]
        )
    except subprocess.CalledProcessError as exc:
        raise click.UsageError(
            f"Failed to create workspace `{name}`:\n{exc.stderr or exc.stdout}".rstrip()
        ) from exc


def prepare_workspace() -> tuple[str, Path]:
    """End-to-end: fetch trunk + create workspace. Returns (name, path)."""
    main_root = main_repo_root()
    fetch_trunk(main_root)
    name = new_workspace_name()
    path = workspace_path(main_root, name)
    create_workspace(main_root, name, path)
    return name, path
