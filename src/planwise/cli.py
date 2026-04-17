"""Planwise CLI — local issue tracker for structured development."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from planwise import __version__
from planwise.agents import VALID_AGENTS as VALID_AGENT_NAMES
from planwise.agents import inject_agent_instructions
from planwise.commands import completion, crud, deps, lifecycle, metadata, query, run, sync, verify
from planwise.frontmatter import parse, to_issue
from planwise.helpers import STATUS_DIR_NAMES, VALID_STATUSES, echo_json, is_text
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
@click.pass_context
def init(
    ctx: click.Context,
    project: str | None,
    prefix: str | None,
    agent: str | None,
    rules: tuple[str, ...],
) -> None:
    """Initialize a new planning directory."""
    planning_dir = get_planning_dir()
    already_exists = planning_dir.is_dir()

    if already_exists and not agent and not rules:
        raise click.UsageError(f"Planning directory already exists: {planning_dir}")
    if already_exists:
        if rules:
            _update_config_rules(planning_dir, rules)
        if agent:
            agent_path, updated = inject_agent_instructions(agent, planning_dir.parent)
            action = "Updated" if updated else "Injected"
            if is_text(ctx):
                click.echo(f"{action} planwise instructions in {agent_path}")
            else:
                echo_json({"agent_config": str(agent_path), "updated": updated})
        elif rules and is_text(ctx):
            click.echo(f"Updated rules: {', '.join(rules)}")
        elif rules:
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
    (planning_dir / "config.json").write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )
    (planning_dir / ".lock").touch()

    agent_path = None
    if agent:
        agent_path, _updated = inject_agent_instructions(agent, planning_dir.parent)

    if is_text(ctx):
        click.echo(
            f"Initialized planwise for project '{project}' (prefix: {prefix}) in {planning_dir}"
        )
        if rules:
            click.echo(f"Rules: {', '.join(rules)}")
        if agent_path:
            click.echo(f"Injected planwise instructions into {agent_path}")
        click.echo("Run 'planwise completion install' to enable tab completion.")
    else:
        result: dict = {"project": project, "prefix": prefix, "path": str(planning_dir)}
        if rules:
            result["rules"] = sorted(set(rules))
        if agent_path:
            result["agent_config"] = str(agent_path)
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
