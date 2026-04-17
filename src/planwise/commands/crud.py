"""Issue CRUD commands: create, view, edit."""

from __future__ import annotations

import json
import sys
from datetime import date

import click

from planwise.completion import IssueSlug
from planwise.helpers import (
    DEFAULT_LABELS,
    STATUS_BACKLOG,
    VALID_AGENTS,
    VALID_STATUSES,
    VALID_TYPES,
    echo_json,
    format_full_issue,
    format_issue_line,
    is_text,
    log,
    slugify,
)
from planwise.store import get_store


def register(cli: click.Group) -> None:
    """Register CRUD commands on the CLI group."""
    cli.add_command(create)
    cli.add_command(view)
    cli.add_command(edit)


@click.command()
@click.argument("type", type=click.Choice(VALID_TYPES))
@click.argument("title")
@click.option("--parent", type=IssueSlug(), default=None, help="Parent issue slug.")
@click.option("--agent", type=click.Choice(VALID_AGENTS), default=None)
@click.option("--label", multiple=True, help="Labels (repeatable).")
@click.option("--body", "body_text", default=None, help="Issue body (alternative to stdin).")
@click.option("--status", type=click.Choice(VALID_STATUSES), default=None, help="Initial status (default: backlog).")
@click.pass_context
def create(
    ctx: click.Context,
    type: str,
    title: str,
    parent: str | None,
    agent: str | None,
    label: tuple[str, ...],
    body_text: str | None,
    status: str | None,
) -> None:
    """Create a new issue. Body from --body flag or stdin."""
    store = get_store(ctx)
    store.require()

    slug = slugify(title)
    if body_text is not None:
        body = body_text + "\n"
    elif not sys.stdin.isatty():
        body = sys.stdin.read()
    else:
        body = ""
    today = date.today().isoformat()
    labels = list(label) if label else DEFAULT_LABELS.get(type, [])

    if agent is None and type in ("sub-feature", "task", "bug"):
        agent = "standard"

    with store.locked():
        if store.slug_exists(slug):
            raise click.UsageError(f"Issue '{slug}' already exists. Choose a different title.")

        if parent is not None:
            store.require_issue(parent)

        issue = {
            "title": title,
            "type": type,
            "status": status or STATUS_BACKLOG,
            "created": today,
            "labels": labels,
        }
        if type == "feature":
            issue["children"] = []
        else:
            issue["parent"] = parent
            issue["dependencies"] = []
        if agent:
            issue["agent"] = agent
        issue["notes"] = []

        store.write_issue(slug, issue, body)

        if parent is not None:
            parent_issue, parent_body = store.require_issue(parent)
            children = parent_issue.get("children", [])
            if slug not in children:
                children.append(slug)
            parent_issue["children"] = children
            store.write_issue(parent, parent_issue, parent_body)

    if is_text(ctx):
        click.echo(slug)
    else:
        echo_json(format_full_issue(slug, issue, body))


@click.command()
@click.argument("slug", type=IssueSlug())
@click.option("--field", default=None, help="Return a specific field value.")
@click.pass_context
def view(ctx: click.Context, slug: str, field: str | None) -> None:
    """View an issue."""
    store = get_store(ctx)
    store.require()
    issue, body = store.require_issue(slug)

    if field is not None:
        valid_scalars = ("status", "title", "type", "created", "parent", "agent", "closed_reason")
        valid_arrays = ("labels", "children", "dependencies", "notes")
        if field in valid_scalars:
            val = issue.get(field)
            click.echo(val if val is not None else "null")
        elif field in valid_arrays:
            click.echo(json.dumps(issue.get(field, []), indent=2))
        else:
            raise click.UsageError(f"Unknown field: {field}")
        return

    if is_text(ctx):
        click.echo(f"# {issue['title']}")
        parts = [f"slug: {slug}", f"status: {issue['status']}", f"type: {issue['type']}", f"created: {issue['created']}"]
        labels = issue.get("labels", [])
        if labels:
            parts.append(f"labels: [{', '.join(labels)}]")
        if issue["type"] == "feature":
            children = issue.get("children", [])
            if children:
                parts.append(f"children: [{', '.join(children)}]")
        else:
            if issue.get("parent"):
                parts.append(f"parent: #{issue['parent']}")
        if issue.get("agent"):
            parts.append(f"agent: {issue['agent']}")
        if issue.get("closed_reason"):
            parts.append(f"closed: {issue['closed_reason']}")
        click.echo(" | ".join(parts))
        click.echo("---")

        if body:
            click.echo(body, nl=False)

        notes = issue.get("notes", [])
        if notes:
            click.echo("")
            click.echo("--- Notes ---")
            for note in notes:
                click.echo(f"[{note['at']}] {note['text']}")
    else:
        echo_json(format_full_issue(slug, issue, body))


@click.command()
@click.argument("slug", type=IssueSlug())
@click.option("--title", "new_title", default=None)
@click.option("--body", "new_body", default=None)
@click.option("--label", multiple=True, help="Add labels.")
@click.option("--remove-label", multiple=True, help="Remove labels.")
@click.option("--parent", "new_parent", type=IssueSlug(), default=None)
@click.option("--clear-parent", is_flag=True)
@click.option("--agent", "new_agent", type=click.Choice(VALID_AGENTS), default=None)
@click.pass_context
def edit(
    ctx: click.Context,
    slug: str,
    new_title: str | None,
    new_body: str | None,
    label: tuple[str, ...],
    remove_label: tuple[str, ...],
    new_parent: str | None,
    clear_parent: bool,
    new_agent: str | None,
) -> None:
    """Edit an issue."""
    store = get_store(ctx)
    store.require()

    with store.locked():
        issue, body = store.require_issue(slug)

        new_slug = slug
        if new_title is not None:
            new_slug = slugify(new_title)
            if new_slug != slug and store.slug_exists(new_slug):
                raise click.UsageError(f"Issue '{new_slug}' already exists. Choose a different title.")
            issue["title"] = new_title

        if label:
            existing = issue.get("labels", [])
            issue["labels"] = sorted(set(existing + list(label)))

        if remove_label:
            existing = issue.get("labels", [])
            issue["labels"] = [lbl for lbl in existing if lbl not in remove_label]

        if clear_parent or new_parent is not None:
            old_parent = issue.get("parent")
            if old_parent is not None:
                old_parent_issue, old_parent_body = store.require_issue(old_parent)
                old_parent_issue["children"] = [
                    c for c in old_parent_issue.get("children", []) if c != slug and c != new_slug
                ]
                store.write_issue(old_parent, old_parent_issue, old_parent_body)

        if clear_parent:
            issue["parent"] = None
        elif new_parent is not None:
            parent_issue, parent_body = store.require_issue(new_parent)
            children = parent_issue.get("children", [])
            effective_slug = new_slug if new_title is not None else slug
            if effective_slug not in children:
                children.append(effective_slug)
            parent_issue["children"] = children
            store.write_issue(new_parent, parent_issue, parent_body)
            issue["parent"] = new_parent

        if new_agent is not None:
            issue["agent"] = new_agent

        if new_body is not None:
            body = new_body + "\n"

        if new_slug != slug:
            store.rename_issue(slug, new_slug)

        store.write_issue(new_slug, issue, body)

    if is_text(ctx):
        log(ctx, f"Issue #{new_slug} updated")
    else:
        echo_json(format_full_issue(new_slug, issue, body))
