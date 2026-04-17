"""Issue lifecycle commands: status, close."""

from __future__ import annotations

import click

from planwise.completion import IssueSlug
from planwise.helpers import (
    STATUS_BACKLOG,
    STATUS_DONE,
    STATUS_IN_PROGRESS,
    STATUS_READY,
    VALID_STATUSES,
    echo_json,
    format_full_issue,
    is_text,
    log,
)
from planwise.store import get_store


def register(cli: click.Group) -> None:
    """Register lifecycle commands on the CLI group."""
    cli.add_command(status)
    cli.add_command(close)


@click.command()
@click.argument("slug", type=IssueSlug())
@click.argument("target", type=click.Choice(VALID_STATUSES))
@click.pass_context
def status(ctx: click.Context, slug: str, target: str) -> None:
    """Set issue status."""
    store = get_store(ctx)
    store.require()

    with store.locked():
        issue, body = store.require_issue(slug)

        if issue["status"] == target:
            if is_text(ctx):
                log(ctx, f"Issue #{slug} is already {target}")
            else:
                echo_json(format_full_issue(slug, issue, body))
            return

        if target in (STATUS_READY, STATUS_IN_PROGRESS):
            deps = issue.get("dependencies", [])
            if deps:
                issues = store.read_all()
                unsatisfied = [
                    d for d in deps
                    if issues.get(d, {}).get("status") != STATUS_DONE
                ]
                if unsatisfied:
                    names = ", ".join(unsatisfied)
                    raise click.UsageError(
                        f"Cannot move {slug} to {target}: blocked by {names}"
                    )

        issue["status"] = target
        store.write_issue(slug, issue, body)

    if is_text(ctx):
        log(ctx, f"Issue #{slug} \u2192 {target}")
    else:
        echo_json(format_full_issue(slug, issue, body))


@click.command()
@click.argument("slug", type=IssueSlug())
@click.option("--reason", default=None, help="Reason for closing.")
@click.pass_context
def close(ctx: click.Context, slug: str, reason: str | None) -> None:
    """Close an issue."""
    store = get_store(ctx)
    store.require()

    with store.locked():
        issue, body = store.require_issue(slug)

        if issue["status"] == STATUS_DONE:
            if is_text(ctx):
                log(ctx, f"Issue #{slug} is already closed")
            else:
                echo_json(format_full_issue(slug, issue, body))
            return

        if reason:
            issue["closed_reason"] = reason
        issue["status"] = STATUS_DONE
        store.write_issue(slug, issue, body)

    if is_text(ctx):
        log(ctx, f"Issue #{slug} \u2192 {STATUS_DONE} (closed)")
    else:
        echo_json(format_full_issue(slug, issue, body))
