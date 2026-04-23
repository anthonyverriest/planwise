"""Pipeline commands: internal helpers called by workflow skills and /next.

State model (see pipeline/state.py): per-slug files under `<planning_dir>/.pipelines/`.
Creation phases (plan/brief/bug) write no state — /next resolves their candidates
from the issue store via `find_latest_creation_candidate`.
"""

from __future__ import annotations

import click

from planwise.agents import VALID_AGENTS
from planwise.pipeline import PHASE_CHAIN, SLUG_CONSUMING_PHASES
from planwise.pipeline.slug import find_latest_creation_candidate
from planwise.pipeline.state import (
    delete_slug_state,
    list_slug_states,
    read_slug_state,
    write_slug_state,
)
from planwise.store import MetaStore, get_store
from planwise.workflows import expand_workflow


_TYPE_TO_NEXT_PHASE: dict[str, str] = {
    "feature": "implement",
    "task": "task",
    "bug": "implement",
}


def register(cli: click.Group) -> None:
    """Register the hidden pipeline helper commands on the CLI group."""
    cli.add_command(pipeline_enter)
    cli.add_command(pipeline_next)


@click.command("pipeline-enter", hidden=True)
@click.argument("phase")
@click.argument("args", nargs=-1)
@click.pass_context
def pipeline_enter(ctx: click.Context, phase: str, args: tuple[str, ...]) -> None:
    """Record that a workflow skill has started. Called from generated SKILL.md files.

    Slug-consuming phases write a per-slug state file so `/next` can advance via
    `PHASE_CHAIN`. Creation phases are a no-op — their candidates are resolved from
    the issue store at `/next` time.
    """
    if phase not in PHASE_CHAIN:
        return

    store = get_store(ctx)
    if not store.planning_dir.is_dir():
        return

    if phase in SLUG_CONSUMING_PHASES and args:
        write_slug_state(store.planning_dir, args[0], {"phase": phase})


@click.command("pipeline-next", hidden=True)
@click.argument("chosen_slug", required=False)
@click.option(
    "--agent",
    type=click.Choice(VALID_AGENTS),
    default="claude",
    show_default=True,
    help="Render the next phase's workflow for the target agent.",
)
@click.pass_context
def pipeline_next(ctx: click.Context, chosen_slug: str | None, agent: str) -> None:
    """Output the next phase's expanded workflow, advancing per-slug state.

    Invoked by the `/next` skill. Run `/clear` first for a fresh context; this
    command's stdout seeds the cleared conversation with the next phase's workflow.

    Resolution order:
    - Explicit slug: advance that slug (via its state file if one exists, else
      treat as a freshly-created creation candidate).
    - No slug: pick the most recently updated slug-consuming pipeline, or fall
      back to the most recently created `ready` feature/task/bug.
    """
    store = get_store(ctx)
    store.require()

    if chosen_slug is not None:
        state = read_slug_state(store.planning_dir, chosen_slug)
        if state and state.get("phase"):
            _advance_slug_consuming(ctx, store, chosen_slug, state["phase"], agent)
            return
        _advance_from_issue_type(ctx, store, chosen_slug, agent)
        return

    states = list_slug_states(store.planning_dir)
    if states:
        slug, state = max(states, key=lambda p: p[1].get("updated_at", ""))
        phase = state.get("phase")
        if not phase:
            raise click.UsageError(
                f"Pipeline state for '{slug}' is corrupted (missing phase)."
            )
        _advance_slug_consuming(ctx, store, slug, phase, agent)
        return

    slug = find_latest_creation_candidate(store)
    if slug is None:
        raise click.UsageError(
            "No active pipeline and no ready feature/task/bug issues to advance. "
            "Start with /plan, /brief, /bug, /implement, /test, /optimize, /memo, or /task."
        )
    _advance_from_issue_type(ctx, store, slug, agent)


def _advance_slug_consuming(
    ctx: click.Context,
    store: MetaStore,
    slug: str,
    current_phase: str,
    agent: str,
) -> None:
    """Walk PHASE_CHAIN for a slug already in flight through a slug-consuming phase."""
    next_phase = PHASE_CHAIN.get(current_phase)
    if next_phase is None:
        click.echo(f"Pipeline complete after '{current_phase}' for #{slug}.")
        delete_slug_state(store.planning_dir, slug)
        return
    _emit_next_phase(ctx, store, next_phase, slug, agent)


def _advance_from_issue_type(
    ctx: click.Context,
    store: MetaStore,
    slug: str,
    agent: str,
) -> None:
    """Advance a slug that has no in-flight state by mapping its issue type to a phase."""
    issue, _body = store.require_issue(slug)
    issue_type = issue.get("type")
    next_phase = _TYPE_TO_NEXT_PHASE.get(issue_type or "")
    if next_phase is None:
        raise click.UsageError(
            f"Issue #{slug} has type '{issue_type}' which has no next phase. "
            "Only feature, task, and bug issues can start a pipeline."
        )
    _emit_next_phase(ctx, store, next_phase, slug, agent)


def _emit_next_phase(
    ctx: click.Context,
    store: MetaStore,
    next_phase: str,
    slug: str,
    agent: str,
) -> None:
    """Expand the next phase's workflow, update per-slug state, and print to stdout."""
    rule_names = list(store.get_config("rules", []) or [])
    content = expand_workflow(next_phase, slug, rule_names, agent=agent)
    if content is None:
        raise click.UsageError(f"Workflow '{next_phase}' not found.")

    if next_phase in SLUG_CONSUMING_PHASES and slug:
        write_slug_state(store.planning_dir, slug, {"phase": next_phase})
    elif slug:
        delete_slug_state(store.planning_dir, slug)

    click.echo(content)
