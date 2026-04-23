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
from pathlib import Path

import click

from planwise.commands._launcher import prepare_workspace


def register(cli: click.Group) -> None:
    """Register the claude command on the CLI group."""
    cli.add_command(claude_cmd)


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
    name, path = prepare_workspace()
    click.echo(f"Created workspace `{name}` at {path}")
    _exec_claude(path)
