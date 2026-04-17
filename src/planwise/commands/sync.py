"""Sync pipeline CLI commands: init, show, exec, state, reset, plugins."""

from __future__ import annotations

from pathlib import Path

import click

from planwise.helpers import echo_json, is_text
from planwise.store import get_planning_dir
from planwise.sync.engine import execute_step
from planwise.sync.errors import SyncError
from planwise.sync.pipeline import load_pipeline, validate_pipeline_plugins
from planwise.sync.plugin_loader import discover_plugins
from planwise.sync.state import create_state, delete_state, read_state, update_step, write_state
from planwise.sync.types import PipelineConfig, Plugin, StepResult, SyncState


def _reconcile_state(sync_state: SyncState, step_names: list[str]) -> None:
    """Reconcile state with pipeline when steps have been added or removed."""
    existing = {sr["step_name"]: sr for sr in sync_state["steps"]}
    reconciled: list[StepResult] = []
    for name in step_names:
        if name in existing:
            reconciled.append(existing[name])
        else:
            reconciled.append(StepResult(step_name=name, status="pending"))
    sync_state["steps"] = reconciled
    sync_state["completed"] = False


def register(cli: click.Group) -> None:
    """Register the sync command group on the CLI group."""
    cli.add_command(sync)


_PIPELINE_TEMPLATE = """\
# Sync pipeline definition.
# See: https://github.com/averriest/planwise#sync

name: deploy
description: "Describe your deployment pipeline"

# Uncomment to add custom plugin directories (relative to this file):
# plugin_dirs:
#   - .planwise/plugins

steps:
  # Example: check Alembic migration heads
  # - name: check-heads
  #   plugin: alembic
  #   action: check-heads
  #   gate: auto

  # Example: inline command (no plugin needed)
  # - name: run-tests
  #   run: uv run pytest
  #   gate: auto

  # Example: manual approval before merge
  # - name: merge-to-prod
  #   plugin: git
  #   action: merge
  #   params:
  #     from: dev
  #     to: prod
  #     remote: origin
  #   gate: human
"""


def _resolve_pipeline_path(pipeline: str) -> Path:
    """Resolve the pipeline path, defaulting to planwise/sync.yml."""
    path = Path(pipeline)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _load_and_validate(pipeline_path: Path) -> tuple[PipelineConfig, dict[str, Plugin]]:
    """Load pipeline config and discover/validate plugins."""
    config = load_pipeline(pipeline_path)
    plugins = discover_plugins(config["plugin_dirs"], pipeline_path.parent)
    validate_pipeline_plugins(config, plugins)
    return config, plugins


@click.group()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Sync pipeline management."""


@sync.command()
@click.option("--pipeline", default="planwise/sync.yml", help="Path to pipeline YAML.")
@click.pass_context
def init(ctx: click.Context, pipeline: str) -> None:
    """Create a starter sync.yml pipeline config."""
    path = _resolve_pipeline_path(pipeline)

    if path.is_file():
        raise click.UsageError(f"Pipeline file already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_PIPELINE_TEMPLATE, encoding="utf-8")

    if is_text(ctx):
        click.echo(f"Created pipeline config at {path}")
        click.echo("Edit the file to define your sync steps, then run: /sync")
    else:
        echo_json({"path": str(path), "created": True})


@sync.command(hidden=True)
@click.option("--pipeline", default="planwise/sync.yml", help="Path to pipeline YAML.")
@click.pass_context
def show(ctx: click.Context, pipeline: str) -> None:
    """Show the pipeline with current state overlay."""
    pipeline_path = _resolve_pipeline_path(pipeline)

    try:
        config, _plugins = _load_and_validate(pipeline_path)
    except SyncError as exc:
        raise click.UsageError(str(exc)) from exc

    planning_dir = get_planning_dir()
    sync_state = read_state(planning_dir) if planning_dir.is_dir() else None

    step_statuses: dict[str, str] = {}
    if sync_state and sync_state["pipeline_name"] == config["name"]:
        for step_result in sync_state["steps"]:
            step_statuses[step_result["step_name"]] = step_result.get("status", "pending")

    steps_output = []
    for i, step in enumerate(config["steps"]):
        status = step_statuses.get(step["name"], "pending")
        entry = {
            "index": i,
            "name": step["name"],
            "plugin": step.get("plugin", ""),
            "action": step.get("action", ""),
            "gate": step.get("gate", "auto"),
            "status": status,
        }
        if "run" in step:
            entry["run"] = step["run"]
        steps_output.append(entry)

    if is_text(ctx):
        click.echo(f"Pipeline: {config['name']}")
        if config["description"]:
            click.echo(f"  {config['description']}")
        click.echo()
        for entry in steps_output:
            status_tag = entry["status"].upper()
            source = entry.get("run") or f"{entry['plugin']}.{entry['action']}"
            gate_tag = f" [{entry['gate']}]" if entry["gate"] == "human" else ""
            click.echo(f"  {entry['index'] + 1}. [{status_tag}] {entry['name']} — {source}{gate_tag}")
    else:
        echo_json({
            "pipeline": config["name"],
            "description": config["description"],
            "steps": steps_output,
            "has_state": sync_state is not None,
            "completed": sync_state["completed"] if sync_state else False,
        })


@sync.command("exec", hidden=True)
@click.argument("step_name")
@click.option("--pipeline", default="planwise/sync.yml", help="Path to pipeline YAML.")
@click.option("--force", is_flag=True, help="Run even if step already succeeded.")
@click.pass_context
def exec_step(ctx: click.Context, step_name: str, pipeline: str, force: bool) -> None:
    """Execute a single pipeline step."""
    pipeline_path = _resolve_pipeline_path(pipeline)

    try:
        config, plugins = _load_and_validate(pipeline_path)
    except SyncError as exc:
        raise click.UsageError(str(exc)) from exc

    target_step = None
    target_index = -1
    for i, step in enumerate(config["steps"]):
        if step["name"] == step_name:
            target_step = step
            target_index = i
            break

    if target_step is None:
        available = ", ".join(s["name"] for s in config["steps"])
        raise click.UsageError(f"Step '{step_name}' not found. Available: {available}")

    planning_dir = get_planning_dir()
    step_names = [s["name"] for s in config["steps"]]
    sync_state = read_state(planning_dir)
    if sync_state is None or sync_state["pipeline_name"] != config["name"]:
        sync_state = create_state(config["name"], step_names)
    else:
        _reconcile_state(sync_state, step_names)

    current_status = "pending"
    for sr in sync_state["steps"]:
        if sr["step_name"] == step_name:
            current_status = sr.get("status", "pending")
            break

    if current_status in ("success", "fixed") and not force:
        if is_text(ctx):
            click.echo(f"Step '{step_name}' already succeeded. Use --force to re-run.")
        else:
            echo_json({"step_name": step_name, "status": current_status, "skipped": True})
        return

    try:
        result = execute_step(target_step, plugins)
    except SyncError as exc:
        raise click.UsageError(str(exc)) from exc

    update_step(sync_state, step_name, result)
    sync_state["current_step"] = target_index
    sync_state["completed"] = all(
        sr.get("status") in ("success", "fixed", "skipped")
        for sr in sync_state["steps"]
    )

    write_state(planning_dir, sync_state)

    if is_text(ctx):
        click.echo(f"Step: {step_name}")
        click.echo(f"Status: {result.get('status', 'unknown')}")
        if "exit_code" in result:
            click.echo(f"Exit code: {result['exit_code']}")
        if result.get("matched_failure"):
            click.echo(f"Matched: {result['matched_failure']}")
        if result.get("fix_command"):
            click.echo(f"Fix attempted: {result['fix_command']}")
        stdout = result.get("stdout", "")
        if stdout.strip():
            click.echo(f"\n--- stdout ---\n{stdout.rstrip()}")
        stderr = result.get("stderr", "")
        if stderr.strip():
            click.echo(f"\n--- stderr ---\n{stderr.rstrip()}")
    else:
        echo_json(result)


@sync.command(hidden=True)
@click.option("--step", default=None, help="Show state for a specific step.")
@click.pass_context
def state(ctx: click.Context, step: str | None) -> None:
    """Show current sync run state."""
    planning_dir = get_planning_dir()

    try:
        sync_state = read_state(planning_dir)
    except SyncError as exc:
        raise click.UsageError(str(exc)) from exc

    if sync_state is None:
        if is_text(ctx):
            click.echo("No active sync run.")
        else:
            echo_json({"active": False})
        return

    if step:
        for sr in sync_state["steps"]:
            if sr["step_name"] == step:
                if is_text(ctx):
                    click.echo(f"Step: {sr['step_name']}")
                    click.echo(f"Status: {sr.get('status', 'pending')}")
                    if sr.get("matched_failure"):
                        click.echo(f"Matched: {sr['matched_failure']}")
                    if sr.get("fix_command"):
                        click.echo(f"Fix: {sr['fix_command']}")
                else:
                    echo_json(sr)
                return
        raise click.UsageError(f"Step '{step}' not found in state")

    if is_text(ctx):
        click.echo(f"Pipeline: {sync_state['pipeline_name']}")
        click.echo(f"Started: {sync_state['started_at']}")
        click.echo(f"Completed: {sync_state['completed']}")
        click.echo()
        for sr in sync_state["steps"]:
            status = sr.get("status", "pending").upper()
            extra = ""
            if sr.get("matched_failure"):
                extra = f" ({sr['matched_failure']})"
            click.echo(f"  [{status}] {sr['step_name']}{extra}")
    else:
        echo_json(sync_state)


@sync.command(hidden=True)
@click.option("--step", default=None, help="Reset a specific step to pending.")
@click.option("--all", "reset_all", is_flag=True, help="Reset entire pipeline state.")
@click.pass_context
def reset(ctx: click.Context, step: str | None, reset_all: bool) -> None:
    """Reset pipeline state to allow re-execution."""
    planning_dir = get_planning_dir()

    if not step and not reset_all:
        raise click.UsageError("Specify --step NAME or --all")

    if reset_all:
        deleted = delete_state(planning_dir)
        if is_text(ctx):
            click.echo("State cleared." if deleted else "No state to clear.")
        else:
            echo_json({"reset": "all", "deleted": deleted})
        return

    try:
        sync_state = read_state(planning_dir)
    except SyncError as exc:
        raise click.UsageError(str(exc)) from exc

    if sync_state is None:
        raise click.UsageError("No active sync run to reset")

    found = False
    for sr in sync_state["steps"]:
        if sr["step_name"] == step:
            sr.clear()
            sr["step_name"] = step
            sr["status"] = "pending"
            found = True
            break

    if not found:
        raise click.UsageError(f"Step '{step}' not found in state")

    sync_state["completed"] = False
    write_state(planning_dir, sync_state)

    if is_text(ctx):
        click.echo(f"Step '{step}' reset to pending.")
    else:
        echo_json({"reset": step})


@sync.command(hidden=True)
@click.option("--pipeline", default="planwise/sync.yml", help="Path to pipeline YAML.")
@click.pass_context
def plugins(ctx: click.Context, pipeline: str) -> None:
    """List available plugins and their actions."""
    pipeline_path = _resolve_pipeline_path(pipeline)

    plugin_dirs: list[str] = []
    if pipeline_path.is_file():
        try:
            config = load_pipeline(pipeline_path)
            plugin_dirs = config["plugin_dirs"]
        except SyncError:
            pass

    try:
        loaded = discover_plugins(plugin_dirs, pipeline_path.parent)
    except SyncError as exc:
        raise click.UsageError(str(exc)) from exc

    if is_text(ctx):
        if not loaded:
            click.echo("No plugins found.")
            return
        for plugin in sorted(loaded.values(), key=lambda p: p["name"]):
            click.echo(f"\n{plugin['name']} — {plugin['description']}")
            for action_name, action in sorted(plugin["actions"].items()):
                timeout = action.get("timeout", 300)
                click.echo(f"  {action_name}: {action['command']} (timeout: {timeout}s)")
    else:
        output = []
        for plugin in sorted(loaded.values(), key=lambda p: p["name"]):
            output.append({
                "name": plugin["name"],
                "description": plugin["description"],
                "actions": list(plugin["actions"].keys()),
            })
        echo_json(output)
