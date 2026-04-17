"""Metadata commands: note, stats."""

from __future__ import annotations

from datetime import datetime, timezone

import click

from planwise.completion import IssueSlug
from planwise.helpers import STATUS_DONE, echo_json, format_full_issue, is_text, log
from planwise.store import get_store


def register(cli: click.Group) -> None:
    """Register metadata commands on the CLI group."""
    cli.add_command(note)
    cli.add_command(stats)


@click.command()
@click.argument("slug", type=IssueSlug())
@click.argument("text")
@click.pass_context
def note(ctx: click.Context, slug: str, text: str) -> None:
    """Append a note to an issue."""
    store = get_store(ctx)
    store.require()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with store.locked():
        issue, body = store.require_issue(slug)
        notes = issue.get("notes", [])
        notes.append({"at": now, "text": text})
        issue["notes"] = notes
        store.write_issue(slug, issue, body)

    if is_text(ctx):
        log(ctx, f"Note added to #{slug}")
    else:
        echo_json(format_full_issue(slug, issue, body))


@click.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Project health overview."""
    store = get_store(ctx)
    store.require()

    issues = store.read_all()
    project = store.get_config("project", "unknown")

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    open_count = 0
    done_count = 0

    for issue in issues.values():
        issue_status = issue["status"]
        issue_type = issue["type"]
        by_status[issue_status] = by_status.get(issue_status, 0) + 1
        by_type[issue_type] = by_type.get(issue_type, 0) + 1
        if issue_status == STATUS_DONE:
            done_count += 1
        else:
            open_count += 1

    result = {
        "project": project,
        "total": len(issues),
        "by_status": by_status,
        "by_type": by_type,
        "open": open_count,
        "done": done_count,
    }

    if is_text(ctx):
        click.echo(f"Project: {project}")
        click.echo(f"Total: {len(issues)} (open: {open_count}, done: {done_count})")
        if by_status:
            click.echo(f"By status: {', '.join(f'{k}: {v}' for k, v in sorted(by_status.items()))}")
        if by_type:
            click.echo(f"By type: {', '.join(f'{k}: {v}' for k, v in sorted(by_type.items()))}")
    else:
        echo_json(result)
