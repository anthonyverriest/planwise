"""Shell completion installation command."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import click

from planwise.helpers import log

_SUPPORTED_SHELLS = ("bash", "zsh", "fish")

_COMPLETION_ENV_VAR = "_PLANWISE_COMPLETE"

_SOURCE_COMMANDS = {
    "bash": "bash_source",
    "zsh": "zsh_source",
    "fish": "fish_source",
}

_RC_FILES = {
    "bash": ".bashrc",
    "zsh": ".zshrc",
}

_COMPLETION_DIRS = {
    "fish": ".config/fish/completions",
}

_MARKER = "# planwise shell completion"


def _detect_shell() -> str:
    """Detect the current shell from SHELL env var."""
    shell_path = os.environ.get("SHELL", "")
    shell_name = Path(shell_path).name
    if shell_name in _SUPPORTED_SHELLS:
        return shell_name
    return "bash"


def _generate_script(shell: str) -> str:
    """Generate the completion script for a given shell."""
    result = subprocess.run(
        ["planwise"],
        env={**os.environ, _COMPLETION_ENV_VAR: _SOURCE_COMMANDS[shell]},
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def register(cli: click.Group) -> None:
    """Register the completion command on the CLI group."""
    cli.add_command(completion)


@click.group()
def completion() -> None:
    """Manage shell completion."""


@completion.command()
@click.argument("shell", required=False, default=None, type=click.Choice(_SUPPORTED_SHELLS))
@click.pass_context
def show(ctx: click.Context, shell: str | None) -> None:
    """Print the completion script to stdout."""
    resolved_shell = shell or _detect_shell()
    script = _generate_script(resolved_shell)
    click.echo(script)


@completion.command()
@click.argument("shell", required=False, default=None, type=click.Choice(_SUPPORTED_SHELLS))
@click.pass_context
def install(ctx: click.Context, shell: str | None) -> None:
    """Install shell completion for planwise."""
    resolved_shell = shell or _detect_shell()
    script = _generate_script(resolved_shell)
    home = Path.home()

    if resolved_shell == "fish":
        target = home / _COMPLETION_DIRS["fish"] / "planwise.fish"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(script + "\n", encoding="utf-8")
        log(ctx, f"Completion installed: {target}")
        return

    rc_file = home / _RC_FILES[resolved_shell]
    if rc_file.is_file():
        content = rc_file.read_text(encoding="utf-8")
        if _MARKER in content:
            log(ctx, f"Completion already installed in {rc_file}")
            return

    eval_line = f'\n{_MARKER}\neval "$({_COMPLETION_ENV_VAR}={_SOURCE_COMMANDS[resolved_shell]} planwise)"\n'

    with rc_file.open("a", encoding="utf-8") as fh:
        fh.write(eval_line)

    log(ctx, f"Completion installed in {rc_file} — restart your shell or run: source {rc_file}")
