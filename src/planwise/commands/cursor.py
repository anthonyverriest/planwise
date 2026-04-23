"""`pw cursor` — create a fresh jj workspace and open it in Cursor.

Mirrors `pw claude` but spawns the `cursor` CLI detached instead of exec'ing:
Cursor is a GUI and its CLI returns immediately after asking the running app
(or cold-starting one) to open a window at the given path. The user's terminal
stays usable; Cursor pops a window scoped to the fresh jj workspace so two
concurrent features never collide on `@`.

Cleanup is manual once the feature is merged:
    jj workspace forget <name>
    rm -rf <path>
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click

from planwise.commands._launcher import prepare_workspace


def register(cli: click.Group) -> None:
    """Register the cursor command on the CLI group."""
    cli.add_command(cursor_cmd)


def _spawn_cursor(cwd: Path) -> None:
    cursor_bin = shutil.which("cursor")
    if cursor_bin is None:
        raise click.UsageError(
            "`cursor` CLI not found on PATH. Install it from Cursor:\n"
            "  Command Palette → \"Shell Command: Install 'cursor' command in PATH\"\n"
            f"…or open the workspace manually:\n"
            f"  cd {cwd}"
        )
    subprocess.Popen(
        [cursor_bin, str(cwd)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


@click.command(name="cursor")
def cursor_cmd() -> None:
    """Create a fresh jj workspace off dev@origin and open it in Cursor.

    Spawns Cursor detached so the terminal stays usable. Every invocation
    yields an isolated sandbox, enabling concurrent Cursor windows that
    cannot clobber each other's working copy. The workspace is named with
    a UTC timestamp (e.g. `wt-20260420-141523-042`) and placed at
    `<repo-parent>/<repo-name>-<name>`. Cleanup is manual via
    `jj workspace forget <name>` + `rm -rf <path>` once the feature ships.
    """
    name, path = prepare_workspace()
    _spawn_cursor(path)
    click.echo(f"Created workspace `{name}` at {path}")
    click.echo("Opening in Cursor — if cold, first window can take a second.")
