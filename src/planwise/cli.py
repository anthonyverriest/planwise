"""Planwise CLI — local issue tracker for structured development."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import click

from planwise import __version__
from planwise.agents import VALID_AGENTS as VALID_AGENT_NAMES
from planwise.agents import inject_agent_instructions, inject_layout_section
from planwise.commands import (
    claude,
    completion,
    crud,
    cursor,
    deps,
    lifecycle,
    metadata,
    pipeline,
    query,
    run,
    sync,
    verify,
)
from planwise.frontmatter import parse, to_issue
from planwise.helpers import STATUS_DIR_NAMES, VALID_STATUSES, echo_json, is_text
from planwise.layouts import validate_layout_callback
from planwise.rulesets import parse_rules_callback
from planwise.store import MetaStore, get_planning_dir


def _read_config(planning_dir: Path) -> dict:
    """Read config.json if present, else return empty dict."""
    config_path = planning_dir / "config.json"
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _write_config(planning_dir: Path, config: dict) -> None:
    """Persist config.json atomically."""
    config_path = planning_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _ensure_structure(planning_dir: Path) -> None:
    """Idempotently create the planwise directory skeleton.

    Safe to re-run: creates missing subdirs and lock file without touching
    existing content.
    """
    issues_dir = planning_dir / "issues"
    issues_dir.mkdir(parents=True, exist_ok=True)
    for status in VALID_STATUSES:
        status_dir = issues_dir / STATUS_DIR_NAMES[status]
        status_dir.mkdir(exist_ok=True)
        gitkeep = status_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    knowledge_dir = planning_dir / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    knowledge_keep = knowledge_dir / ".gitkeep"
    if not knowledge_keep.exists():
        knowledge_keep.touch()

    lock = planning_dir / ".lock"
    if not lock.exists():
        lock.touch()


def _ensure_vcs(project_dir: Path) -> dict:
    """Ensure a colocated jj+git repo exists at project_dir.

    Planwise workflows require jj colocated with git. If `.jj/` is absent,
    run `jj git init --colocate` (works whether or not `.git/` already exists).
    No-op if `.jj/` is present. Hard-errors if the `jj` binary is missing,
    since downstream workflows cannot run without it.
    """
    jj_dir = project_dir / ".jj"
    git_dir = project_dir / ".git"

    if jj_dir.is_dir():
        return {"action": "skipped", "reason": "jj already initialized"}

    if shutil.which("jj") is None:
        raise click.UsageError(
            "jj is required by planwise workflows but was not found on PATH. "
            "Install from https://jj-vcs.github.io/jj/ or re-run with --no-vcs."
        )

    had_git = git_dir.is_dir()
    try:
        subprocess.run(
            ["jj", "git", "init", "--colocate"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise click.ClickException(
            f"`jj git init --colocate` failed: {e.stderr.strip() or e.stdout.strip()}"
        ) from e

    return {
        "action": "colocated" if had_git else "initialized",
        "jj": True,
        "git": True,
    }


def _seed_layout(layout: str, project_dir: Path, agent: str) -> tuple[Path, bool]:
    """Append the layout section to the active agent's instruction file.

    Warns via stderr if the <layout> section is already present (user edits preserved).
    """
    path, skipped = inject_layout_section(layout, project_dir, agent=agent)
    if skipped:
        click.echo(
            f"Layout already present in {path}; skipping "
            "(edit the <layout> section directly, or delete it to re-seed).",
            err=True,
        )
    return path, skipped


@click.group()
@click.option("--text", "-t", is_flag=True, help="Human-readable output instead of JSON.")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx: click.Context, text: bool) -> None:
    """Planwise CLI entry point."""
    ctx.ensure_object(dict)
    ctx.obj["text"] = text or os.environ.get("PLANWISE_OUTPUT", "") == "text"
    ctx.obj["store"] = MetaStore()


@cli.command()
@click.option("--project", required=False, default=None, help="Project name (required for first init).")
@click.option("--prefix", required=False, default=None, help="Issue prefix, e.g. PW (required for first init).")
@click.option(
    "--agent",
    type=click.Choice(VALID_AGENT_NAMES),
    default=None,
    help="Inject planwise instructions into agent config (e.g. CLAUDE.md).",
)
@click.option(
    "--rules",
    "rules",
    multiple=True,
    callback=parse_rules_callback,
    is_eager=True,
    expose_value=True,
    help="Ruleset to inject into coding workflows (comma-separated or repeatable).",
)
@click.option(
    "--layout",
    "layout",
    default=None,
    callback=validate_layout_callback,
    help="Package-layout preset to seed into the active agent's instruction file (one-time, user-owned after).",
)
@click.option(
    "--no-vcs",
    "no_vcs",
    is_flag=True,
    default=False,
    help="Skip jj/git colocated init (not recommended; workflows assume jj).",
)
@click.pass_context
def init(
    ctx: click.Context,
    project: str | None,
    prefix: str | None,
    agent: str | None,
    rules: tuple[str, ...],
    layout: str | None,
    no_vcs: bool,
) -> None:
    """Initialize or reconcile the planning directory.

    Idempotent: safe to re-run. Missing directories are created, existing
    config is merged (not overwritten), and identity fields (project, prefix)
    cannot be silently changed once set.
    """
    planning_dir = get_planning_dir()
    existing = _read_config(planning_dir)
    is_initialized = bool(existing.get("project") and existing.get("prefix"))

    if is_initialized:
        if project and project != existing["project"]:
            raise click.UsageError(
                f"--project mismatch: config has '{existing['project']}', got '{project}'. "
                "Edit config.json directly to rename."
            )
        if prefix and prefix != existing["prefix"]:
            raise click.UsageError(
                f"--prefix mismatch: config has '{existing['prefix']}', got '{prefix}'. "
                "Edit config.json directly to rename."
            )
        final_project = existing["project"]
        final_prefix = existing["prefix"]
    else:
        if not project or not prefix:
            raise click.UsageError("--project and --prefix are required for first init.")
        final_project = project
        final_prefix = prefix

    vcs_result: dict | None = None
    if not no_vcs and not is_initialized:
        vcs_result = _ensure_vcs(planning_dir.parent)

    _ensure_structure(planning_dir)

    config: dict = {**existing, "project": final_project, "prefix": final_prefix}
    if agent:
        config["agent"] = agent
    if rules:
        merged_rules = set(config.get("rules", [])) | set(rules)
        config["rules"] = sorted(merged_rules)
    if layout:
        config["layout"] = layout
    _write_config(planning_dir, config)

    agent_path = None
    agent_updated = False
    if agent:
        agent_path, agent_updated = inject_agent_instructions(agent, planning_dir.parent)

    layout_path = None
    layout_skipped = False
    if layout:
        layout_agent = agent or existing.get("agent") or "claude"
        if not agent:
            inject_agent_instructions(layout_agent, planning_dir.parent)
        layout_path, layout_skipped = _seed_layout(layout, planning_dir.parent, layout_agent)

    if is_text(ctx):
        verb = "Reconciled" if is_initialized else "Initialized"
        click.echo(
            f"{verb} planwise for project '{final_project}' (prefix: {final_prefix}) in {planning_dir}"
        )
        if vcs_result and vcs_result.get("action") == "initialized":
            click.echo(f"Initialized colocated jj+git repo in {planning_dir.parent}")
        elif vcs_result and vcs_result.get("action") == "colocated":
            click.echo(f"Added jj colocation to existing git repo in {planning_dir.parent}")
        if config.get("rules"):
            click.echo(f"Rules: {', '.join(config['rules'])}")
        if agent_path:
            action = "Updated" if agent_updated else "Injected"
            click.echo(f"{action} planwise instructions in {agent_path}")
        if layout_path and not layout_skipped:
            click.echo(f"Seeded '{layout}' layout into {layout_path}")
        if not is_initialized:
            click.echo("Run 'planwise completion install' to enable tab completion.")
    else:
        result: dict = {
            "project": final_project,
            "prefix": final_prefix,
            "path": str(planning_dir),
            "reconciled": is_initialized,
        }
        if vcs_result:
            result["vcs"] = vcs_result
        if config.get("rules"):
            result["rules"] = config["rules"]
        if agent_path:
            result["agent_config"] = str(agent_path)
            result["agent_updated"] = agent_updated
        if layout:
            result["layout"] = layout
        if layout_path:
            result["layout_path"] = str(layout_path)
            result["layout_skipped"] = layout_skipped
        echo_json(result)


@cli.command()
@click.pass_context
def migrate(ctx: click.Context) -> None:
    """Migrate flat issue files into status subdirectories."""
    store = ctx.obj["store"]
    store.require()

    issues_dir = store.issues_dir
    moved: list[dict[str, str]] = []

    for status in VALID_STATUSES:
        status_dir = issues_dir / STATUS_DIR_NAMES[status]
        status_dir.mkdir(exist_ok=True)
        gitkeep = status_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    for path in sorted(issues_dir.glob("*.md")):
        if path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8")
        raw, _body = parse(text)
        issue = to_issue(raw)
        target_dir = issues_dir / STATUS_DIR_NAMES[issue["status"]]
        target_path = target_dir / path.name
        path.rename(target_path)
        moved.append({"slug": path.stem, "status": issue["status"]})

    root_gitkeep = issues_dir / ".gitkeep"
    if root_gitkeep.exists():
        root_gitkeep.unlink()

    if is_text(ctx):
        if not moved:
            click.echo("Nothing to migrate")
        else:
            for entry in moved:
                click.echo(f"  {entry['slug']} -> {entry['status']}/")
            click.echo(f"Migrated {len(moved)} issue(s)")
    else:
        echo_json({"migrated": len(moved), "issues": moved})


claude.register(cli)
completion.register(cli)
crud.register(cli)
cursor.register(cli)
lifecycle.register(cli)
query.register(cli)
deps.register(cli)
metadata.register(cli)
run.register(cli)
pipeline.register(cli)
sync.register(cli)
verify.register(cli)
