"""Planwise CLI — local issue tracker for structured development."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from planwise import __version__
from planwise.agents import VALID_AGENTS as VALID_AGENT_NAMES
from planwise.agents import inject_agent_instructions, inject_layout_section
from planwise.commands import completion, crud, deps, lifecycle, metadata, query, run, sync, verify
from planwise.frontmatter import parse, to_issue
from planwise.helpers import STATUS_DIR_NAMES, VALID_STATUSES, echo_json, is_text
from planwise.layouts import validate_layout_callback
from planwise.rulesets import parse_rules_callback
from planwise.store import MetaStore, get_planning_dir


def _update_config_rules(planning_dir: Path, rules: tuple[str, ...]) -> None:
    """Merge new rulesets into the existing config.json rules list."""
    config_path = planning_dir / "config.json"
    config: dict = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    existing: list[str] = config.get("rules", [])
    merged = sorted(set(existing) | set(rules))
    config["rules"] = merged
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _update_config_layout(planning_dir: Path, layout: str) -> None:
    """Persist the selected layout name into config.json."""
    config_path = planning_dir / "config.json"
    config: dict = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    config["layout"] = layout
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def _seed_layout(layout: str, project_dir: Path) -> tuple[Path, bool]:
    """Seed layout into planwise/layout.md and reference it from CLAUDE.md.

    Warns via stderr if the layout file already exists (user edits preserved).
    """
    path, skipped = inject_layout_section(layout, project_dir)
    if skipped:
        click.echo(
            f"Layout file already present at {path}; skipping "
            "(edit it directly, or delete to re-seed).",
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
    help="Package-layout preset to seed into the project's CLAUDE.md (one-time, user-owned after).",
)
@click.pass_context
def init(
    ctx: click.Context,
    project: str | None,
    prefix: str | None,
    agent: str | None,
    rules: tuple[str, ...],
    layout: str | None,
) -> None:
    """Initialize a new planning directory."""
    planning_dir = get_planning_dir()
    already_exists = planning_dir.is_dir()

    if already_exists and not agent and not rules and not layout:
        raise click.UsageError(f"Planning directory already exists: {planning_dir}")
    if already_exists:
        if rules:
            _update_config_rules(planning_dir, rules)
        if layout:
            _update_config_layout(planning_dir, layout)
        if agent:
            agent_path, updated = inject_agent_instructions(agent, planning_dir.parent)
            action = "Updated" if updated else "Injected"
            if is_text(ctx):
                click.echo(f"{action} planwise instructions in {agent_path}")
            else:
                echo_json({"agent_config": str(agent_path), "updated": updated})
        if layout:
            layout_path, skipped = _seed_layout(layout, planning_dir.parent)
            if is_text(ctx) and not skipped:
                click.echo(f"Seeded '{layout}' layout into {layout_path}")
            elif not is_text(ctx):
                echo_json(
                    {"layout": layout, "layout_path": str(layout_path), "skipped": skipped}
                )
        if rules and not agent and not layout:
            if is_text(ctx):
                click.echo(f"Updated rules: {', '.join(rules)}")
            else:
                echo_json({"rules": list(rules)})
        return

    if not project or not prefix:
        raise click.UsageError("--project and --prefix are required for first init.")

    issues_dir = planning_dir / "issues"
    issues_dir.mkdir(parents=True)

    for status in VALID_STATUSES:
        status_dir = issues_dir / STATUS_DIR_NAMES[status]
        status_dir.mkdir()
        (status_dir / ".gitkeep").touch()

    knowledge_dir = planning_dir / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / ".gitkeep").touch()

    config: dict[str, object] = {"project": project, "prefix": prefix}
    if agent:
        config["agent"] = agent
    if rules:
        config["rules"] = sorted(set(rules))
    if layout:
        config["layout"] = layout
    (planning_dir / "config.json").write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )
    (planning_dir / ".lock").touch()

    agent_path = None
    if agent:
        agent_path, _updated = inject_agent_instructions(agent, planning_dir.parent)

    layout_path = None
    if layout:
        layout_path, _skipped = _seed_layout(layout, planning_dir.parent)

    if is_text(ctx):
        click.echo(
            f"Initialized planwise for project '{project}' (prefix: {prefix}) in {planning_dir}"
        )
        if rules:
            click.echo(f"Rules: {', '.join(rules)}")
        if agent_path:
            click.echo(f"Injected planwise instructions into {agent_path}")
        if layout_path:
            click.echo(f"Seeded '{layout}' layout into {layout_path}")
        click.echo("Run 'planwise completion install' to enable tab completion.")
    else:
        result: dict = {"project": project, "prefix": prefix, "path": str(planning_dir)}
        if rules:
            result["rules"] = sorted(set(rules))
        if agent_path:
            result["agent_config"] = str(agent_path)
        if layout:
            result["layout"] = layout
        if layout_path:
            result["layout_path"] = str(layout_path)
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


completion.register(cli)
crud.register(cli)
lifecycle.register(cli)
query.register(cli)
deps.register(cli)
metadata.register(cli)
run.register(cli)
sync.register(cli)
verify.register(cli)
