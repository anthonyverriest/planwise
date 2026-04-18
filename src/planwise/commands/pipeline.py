"""Pipeline commands: internal helpers called by workflow skills and /next."""

from __future__ import annotations

import click

from planwise.pipeline import CREATION_PHASES, PHASE_CHAIN, SLUG_CONSUMING_PHASES
from planwise.pipeline.slug import list_new_candidates
from planwise.pipeline.state import PipelineState, clear_state, read_state, write_state
from planwise.store import get_store
from planwise.workflows import expand_workflow


_TYPE_TO_NEXT_PHASE: dict[str, str] = {
    "feature": "implement",
    "task": "task",
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
    """Record that a workflow skill has started. Called from generated SKILL.md files."""
    if phase not in PHASE_CHAIN:
        return

    store = get_store(ctx)
    if not store.planning_dir.is_dir():
        return

    existing = read_state(store.planning_dir) or {}

    slug: str | None = existing.get("slug")
    if phase in SLUG_CONSUMING_PHASES and args:
        slug = args[0]

    snapshot: list[str] = []
    if phase in CREATION_PHASES:
        if existing.get("phase") in CREATION_PHASES:
            snapshot = list(existing.get("snapshot", []))
        else:
            snapshot = store.list_slugs()

    state: PipelineState = {"phase": phase, "slug": slug, "snapshot": snapshot}
    write_state(store.planning_dir, state)


@click.command("pipeline-next", hidden=True)
@click.argument("chosen_slug", required=False)
@click.pass_context
def pipeline_next(ctx: click.Context, chosen_slug: str | None) -> None:
    """Output the next phase's expanded workflow, advancing pipeline state.

    Invoked by the `/next` skill. Run `/clear` first for a fresh context; this
    command's stdout seeds the cleared conversation with the next phase's
    workflow.

    When the current phase is a creation phase (plan/brief) and multiple new
    issues were created since the planning session began, this command prints
    the candidate list and exits without advancing. The caller re-runs as
    `/next <slug>` to pick a specific candidate.
    """
    store = get_store(ctx)
    store.require()

    state = read_state(store.planning_dir)
    if not state:
        raise click.UsageError(
            "No active pipeline. Start with /plan, /brief, /implement, "
            "/test, /optimize, /memo, or /task first."
        )

    current = state.get("phase")
    if not current:
        raise click.UsageError("Pipeline state is corrupted (missing phase).")

    if current in CREATION_PHASES:
        _advance_from_creation(ctx, store, state, current, chosen_slug)
        return

    _advance_from_slug_phase(ctx, store, state, current)


def _advance_from_creation(
    ctx: click.Context,
    store,
    state: PipelineState,
    current: str,
    chosen_slug: str | None,
) -> None:
    """Handle /next when the current phase is `plan` or `brief`."""
    before = set(state.get("snapshot", []))
    after = set(store.list_slugs())
    candidates = list_new_candidates(before, after, store)

    if not candidates:
        raise click.UsageError(
            f"Phase '{current}' did not create any new feature or task issues. "
            "Nothing to advance to."
        )

    if chosen_slug is not None:
        match = next((c for c in candidates if c[0] == chosen_slug), None)
        if match is None:
            options = ", ".join(s for s, _ in candidates)
            raise click.UsageError(
                f"'{chosen_slug}' is not in the candidate list. Options: {options}"
            )
        slug, issue_type = match
    elif len(candidates) == 1:
        slug, issue_type = candidates[0]
    else:
        click.echo("Multiple issues created during this planning session:")
        for s, t in candidates:
            click.echo(f"  [{t:<7}] {s}")
        click.echo()
        click.echo("Re-run as: /next <slug>  to pick one.")
        return

    next_phase = _TYPE_TO_NEXT_PHASE[issue_type]
    _emit_next_phase(ctx, store, next_phase, slug)


def _advance_from_slug_phase(
    ctx: click.Context,
    store,
    state: PipelineState,
    current: str,
) -> None:
    """Handle /next when the current phase is slug-consuming (implement/test/etc.)."""
    next_phase = PHASE_CHAIN.get(current)
    if next_phase is None:
        click.echo(f"Pipeline complete after '{current}'. Nothing to advance to.")
        clear_state(store.planning_dir)
        return

    slug = state.get("slug")
    if next_phase in SLUG_CONSUMING_PHASES and not slug:
        raise click.UsageError(
            f"Cannot advance to '{next_phase}': no slug available in pipeline state."
        )
    _emit_next_phase(ctx, store, next_phase, slug or "")


def _emit_next_phase(
    ctx: click.Context,
    store,
    next_phase: str,
    slug: str,
) -> None:
    """Expand the next phase's workflow, update state, and print to stdout."""
    rule_names = list(store.get_config("rules", []) or [])
    content = expand_workflow(next_phase, slug, rule_names)
    if content is None:
        raise click.UsageError(f"Workflow '{next_phase}' not found.")

    new_state: PipelineState = {
        "phase": next_phase,
        "slug": slug or None,
        "snapshot": [],
    }
    write_state(store.planning_dir, new_state)

    click.echo(content)
