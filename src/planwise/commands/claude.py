"""`pw claude` — create a fresh jj workspace and exec Claude Code inside it.

Each invocation produces a disposable, isolated jj workspace off `dev@origin`.
Concurrent invocations never collide on `@` because every workspace has its
own working copy, while sharing the same `.jj/repo/` backend. Intra-feature
parallelism (subagent git worktrees) continues inside each session.

Cleanup is manual once the feature is merged:
    jj workspace forget <name>
    rm -rf <path>
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click


TRUNK_REVSET = "dev@origin"
WORKSPACE_PREFIX = "wt-"


def register(cli: click.Group) -> None:
    """Register the claude command on the CLI group."""
    cli.add_command(claude_cmd)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def _main_repo_root() -> Path:
    """Return the main git working tree root.

    In colocated jj repos, jj workspaces are git worktrees. `git worktree list`
    always lists the main tree first, regardless of which workspace we are
    invoked from — so this resolves correctly whether `pw claude` is called
    from the default workspace or from inside another feature workspace.
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


def _new_workspace_name() -> str:
    now = datetime.now(timezone.utc)
    return f"{WORKSPACE_PREFIX}{now.strftime('%Y%m%d-%H%M%S')}-{now.microsecond // 1000:03d}"


def _workspace_path(main_root: Path, name: str) -> Path:
    return main_root.parent / f"{main_root.name}-{name}"


def _fetch_trunk(main_root: Path) -> None:
    try:
        _run(["jj", "--repository", str(main_root), "git", "fetch"])
    except subprocess.CalledProcessError as exc:
        raise click.UsageError(
            f"`jj git fetch` failed:\n{exc.stderr or exc.stdout}".rstrip()
        ) from exc


def _create_workspace(main_root: Path, name: str, path: Path) -> None:
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


def _exec_claude(cwd: Path) -> None:
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise click.UsageError(
            "`claude` CLI not found on PATH. Install Claude Code or cd manually:\n"
            f"  cd {cwd}"
        )
    os.chdir(cwd)
    os.execvp(claude_bin, [claude_bin])


@click.command(name="claude")
def claude_cmd() -> None:
    """Create a fresh jj workspace off dev@origin and exec claude inside it.

    Every invocation yields an isolated sandbox, enabling concurrent sessions
    that cannot clobber each other's working-copy commit. The workspace is
    named with a UTC timestamp (e.g. `wt-20260420-141523-042`) and placed at
    `<repo-parent>/<repo-name>-<name>`. Cleanup is manual via
    `jj workspace forget <name>` + `rm -rf <path>` once the feature ships.
    """
    main_root = _main_repo_root()
    _fetch_trunk(main_root)
    name = _new_workspace_name()
    path = _workspace_path(main_root, name)
    _create_workspace(main_root, name, path)
    click.echo(f"Created workspace `{name}` at {path}")
    _exec_claude(path)
