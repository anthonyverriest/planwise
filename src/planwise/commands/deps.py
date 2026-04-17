"""Dependency management commands: dep add, dep remove, dep list."""

from __future__ import annotations

import click

from planwise.completion import IssueSlug
from planwise.helpers import echo_json, format_full_issue, is_text, log
from planwise.store import get_store


def register(cli: click.Group) -> None:
    """Register the dep command group on the CLI group."""
    cli.add_command(dep)


@click.group()
@click.pass_context
def dep(ctx: click.Context) -> None:
    """Manage dependencies."""


@dep.command("add")
@click.argument("slug", type=IssueSlug())
@click.argument("dep_slug", type=IssueSlug())
@click.pass_context
def dep_add(ctx: click.Context, slug: str, dep_slug: str) -> None:
    """Add a dependency."""
    store = get_store(ctx)
    store.require()

    if slug == dep_slug:
        raise click.UsageError("Cannot depend on self")

    with store.locked():
        issues = store.read_all()

        if slug not in issues:
            raise click.UsageError(f"Issue #{slug} not found")
        if dep_slug not in issues:
            raise click.UsageError(f"Issue #{dep_slug} not found")

        existing = issues[slug].get("dependencies", [])
        if dep_slug in existing:
            if is_text(ctx):
                log(ctx, f"#{dep_slug} is already a dependency of #{slug}")
            else:
                issue, body = store.require_issue(slug)
                echo_json(format_full_issue(slug, issue, body))
            return

        visited = {dep_slug}
        queue = [dep_slug]
        while queue:
            next_queue: list[str] = []
            for node in queue:
                node_deps = issues.get(node, {}).get("dependencies", [])
                for dep_node in node_deps:
                    if dep_node == slug:
                        raise click.UsageError(f"Cycle detected: #{slug} \u2192 #{dep_slug} \u2192 ... \u2192 #{slug}")
                    if dep_node not in visited:
                        visited.add(dep_node)
                        next_queue.append(dep_node)
            queue = next_queue

        issue, body = store.require_issue(slug)
        deps = issue.get("dependencies", [])
        deps.append(dep_slug)
        issue["dependencies"] = sorted(set(deps))
        store.write_issue(slug, issue, body)

    if is_text(ctx):
        log(ctx, f"#{slug} now depends on #{dep_slug}")
    else:
        echo_json(format_full_issue(slug, issue, body))


@dep.command("remove")
@click.argument("slug", type=IssueSlug())
@click.argument("dep_slug", type=IssueSlug())
@click.pass_context
def dep_remove(ctx: click.Context, slug: str, dep_slug: str) -> None:
    """Remove a dependency."""
    store = get_store(ctx)
    store.require()

    with store.locked():
        issue, body = store.require_issue(slug)
        deps = issue.get("dependencies", [])
        issue["dependencies"] = [d for d in deps if d != dep_slug]
        store.write_issue(slug, issue, body)

    if is_text(ctx):
        log(ctx, f"Removed #{dep_slug} from #{slug} dependencies")
    else:
        echo_json(format_full_issue(slug, issue, body))


@dep.command("list")
@click.argument("slug", type=IssueSlug())
@click.pass_context
def dep_list(ctx: click.Context, slug: str) -> None:
    """List dependencies of an issue."""
    store = get_store(ctx)
    store.require()

    issue, _body = store.require_issue(slug)
    issue_deps = issue.get("dependencies", [])

    issues = store.read_all()
    results = []
    for dep_entry in issue_deps:
        dep_issue = issues.get(dep_entry)
        if dep_issue:
            results.append((dep_entry, dep_issue))

    if is_text(ctx):
        if not results:
            click.echo("No dependencies")
            return
        for dep_slug, dep_issue in results:
            click.echo(f"#{dep_slug} [{dep_issue['status']}] {dep_issue['title']}")
    else:
        echo_json([
            {"slug": dep_slug, "title": dep_issue["title"], "status": dep_issue["status"]}
            for dep_slug, dep_issue in results
        ])
