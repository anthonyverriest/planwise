"""Query commands: list, ready, blocked, search, next."""

from __future__ import annotations

import re

import click

from planwise.completion import IssueSlug
from planwise.helpers import (
    STATUS_BACKLOG,
    STATUS_DONE,
    STATUS_READY,
    VALID_STATUSES,
    VALID_TYPES,
    echo_json,
    format_full_issue,
    format_issue_line,
    is_text,
    resolve_scope,
)
from planwise.store import get_store


def register(cli: click.Group) -> None:
    """Register query commands on the CLI group."""
    cli.add_command(list_issues)
    cli.add_command(ready)
    cli.add_command(blocked)
    cli.add_command(search)
    cli.add_command(next_issue)


@click.command("list")
@click.argument("type_arg", required=False, default=None, type=click.Choice(VALID_TYPES))
@click.option("--status", "status_filter", type=click.Choice(VALID_STATUSES), default=None)
@click.option("--children-of", type=IssueSlug(), default=None)
@click.option("--type", "type_opt", type=click.Choice(VALID_TYPES), default=None)
@click.pass_context
def list_issues(
    ctx: click.Context,
    type_arg: str | None,
    status_filter: str | None,
    children_of: str | None,
    type_opt: str | None,
) -> None:
    """List issues."""
    store = get_store(ctx)
    store.require()

    type_filter = type_opt or type_arg
    issues = store.read_all()

    if children_of is not None and children_of not in issues:
        raise click.UsageError(f"Issue #{children_of} not found")

    scope_slugs = resolve_scope(issues, children_of)

    results = []
    for slug in scope_slugs:
        issue = issues.get(slug)
        if issue is None:
            continue
        if type_filter and issue["type"] != type_filter:
            continue
        if status_filter and issue["status"] != status_filter:
            continue
        if not status_filter and children_of is None and issue["status"] == STATUS_DONE:
            continue
        results.append((slug, issue))

    if is_text(ctx):
        if not results:
            click.echo("No issues found")
            return
        for slug, issue in results:
            click.echo(format_issue_line(slug, issue))
    else:
        echo_json([format_full_issue(slug, issue) for slug, issue in results])


@click.command()
@click.option("--children-of", type=IssueSlug(), default=None)
@click.pass_context
def ready(ctx: click.Context, children_of: str | None) -> None:
    """Issues with all dependencies satisfied."""
    store = get_store(ctx)
    store.require()

    issues = store.read_all()

    if children_of is not None and children_of not in issues:
        raise click.UsageError(f"Issue #{children_of} not found")

    scope_slugs = resolve_scope(issues, children_of)

    results = []
    orphaned_deps: list[tuple[str, list[str]]] = []
    for slug in scope_slugs:
        issue = issues.get(slug)
        if issue is None:
            continue
        if issue["status"] not in (STATUS_BACKLOG, STATUS_READY):
            continue
        deps = issue.get("dependencies", [])
        orphaned = [d for d in deps if d not in issues]
        if orphaned:
            orphaned_deps.append((slug, orphaned))
        if all(issues.get(dep_slug, {}).get("status") == STATUS_DONE for dep_slug in deps):
            results.append((slug, issue))

    for slug, orphaned in orphaned_deps:
        click.echo(
            f"warning: #{slug} depends on non-existent issue(s): "
            f"{', '.join(f'#{d}' for d in orphaned)}. "
            f"Run: planwise verify --fix",
            err=True,
        )

    if is_text(ctx):
        if not results:
            click.echo("No ready issues")
            return
        for slug, issue in results:
            click.echo(format_issue_line(slug, issue))
    else:
        echo_json([format_full_issue(slug, issue) for slug, issue in results])


@click.command()
@click.option("--children-of", type=IssueSlug(), default=None)
@click.pass_context
def blocked(ctx: click.Context, children_of: str | None) -> None:
    """Issues with unsatisfied dependencies."""
    store = get_store(ctx)
    store.require()

    issues = store.read_all()

    if children_of is not None and children_of not in issues:
        raise click.UsageError(f"Issue #{children_of} not found")

    scope_slugs = resolve_scope(issues, children_of)

    results = []
    for slug in scope_slugs:
        issue = issues.get(slug)
        if issue is None:
            continue
        if issue["status"] == STATUS_DONE:
            continue
        deps = issue.get("dependencies", [])
        blockers = [
            dep_slug for dep_slug in deps
            if issues.get(dep_slug, {}).get("status") != STATUS_DONE
        ]
        if blockers:
            results.append((slug, issue, blockers))

    if is_text(ctx):
        if not results:
            click.echo("No blocked issues")
            return
        for slug, issue, blockers in results:
            blocker_strs = []
            for blocker in blockers:
                if blocker in issues:
                    blocker_strs.append(f"#{blocker} ({issues[blocker]['status']})")
                else:
                    blocker_strs.append(f"#{blocker} (NOT FOUND)")
            click.echo(
                f"#{slug} [{issue['status']}] {issue['type']}: {issue['title']}"
                f" \u2014 blocked by {', '.join(blocker_strs)}"
            )
    else:
        out = []
        for slug, issue, blockers in results:
            blocked_by = []
            for b in blockers:
                if b in issues:
                    blocked_by.append(
                        {"slug": b, "title": issues[b]["title"], "status": issues[b]["status"]}
                    )
                else:
                    blocked_by.append({"slug": b, "status": "not-found"})
            out.append({
                "slug": slug,
                "title": issue["title"],
                "type": issue["type"],
                "status": issue["status"],
                "blocked_by": blocked_by,
            })
        echo_json(out)


@click.command()
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, query: str) -> None:
    """Search issue titles and bodies."""
    store = get_store(ctx)
    store.require()

    issues = store.read_all()
    pattern = re.compile(re.escape(query), re.IGNORECASE)

    found_slugs: set[str] = set()

    for slug, issue in issues.items():
        if pattern.search(issue["title"]):
            found_slugs.add(slug)

    for slug in issues:
        if slug in found_slugs:
            continue
        result = store.read_issue(slug)
        if result is None:
            continue
        _issue, body = result
        if body and pattern.search(body):
            found_slugs.add(slug)

    results = [(slug, issues[slug]) for slug in sorted(found_slugs) if slug in issues]

    if is_text(ctx):
        if not results:
            click.echo(f'No issues matching "{query}"')
            return
        for slug, issue in results:
            click.echo(format_issue_line(slug, issue))
    else:
        echo_json([format_full_issue(slug, issue) for slug, issue in results])


@click.command("next")
@click.option("--children-of", type=IssueSlug(), default=None)
@click.pass_context
def next_issue(ctx: click.Context, children_of: str | None) -> None:
    """Pick the next actionable issue (first ready, with full context)."""
    store = get_store(ctx)
    store.require()

    issues = store.read_all()

    if children_of is not None and children_of not in issues:
        raise click.UsageError(f"Issue #{children_of} not found")

    scope_slugs = resolve_scope(issues, children_of)

    orphaned_warned = False
    for slug in scope_slugs:
        issue = issues.get(slug)
        if issue is None:
            continue
        if issue["status"] not in (STATUS_BACKLOG, STATUS_READY):
            continue
        deps = issue.get("dependencies", [])
        orphaned = [d for d in deps if d not in issues]
        if orphaned and not orphaned_warned:
            click.echo(
                f"warning: #{slug} depends on non-existent issue(s): "
                f"{', '.join(f'#{d}' for d in orphaned)}. "
                f"Run: planwise verify --fix",
                err=True,
            )
            orphaned_warned = True
        if not all(issues.get(dep, {}).get("status") == STATUS_DONE for dep in deps):
            continue

        if is_text(ctx):
            click.echo(format_issue_line(slug, issue))
        else:
            result = store.read_issue(slug)
            body = result[1] if result else ""
            echo_json(format_full_issue(slug, issue, body))
        return

    if is_text(ctx):
        click.echo("No actionable issues")
    else:
        echo_json(None)
