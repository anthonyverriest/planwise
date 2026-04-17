"""Shared helpers: slugify, formatting, validation, logging."""

from __future__ import annotations

import json
import re

import click

from planwise.types import Issue


VALID_TYPES = ("feature", "sub-feature", "task", "uat", "bug")
VALID_STATUSES = ("backlog", "ready", "in-progress", "in-review", "done")
VALID_AGENTS = ("standard", "explore-first")

STATUS_BACKLOG = "backlog"
STATUS_READY = "ready"
STATUS_IN_PROGRESS = "in-progress"
STATUS_IN_REVIEW = "in-review"
STATUS_DONE = "done"

STATUS_DIR_NAMES: dict[str, str] = {
    "backlog": "1-backlog",
    "ready": "2-ready",
    "in-progress": "3-in-progress",
    "in-review": "4-in-review",
    "done": "5-done",
}

DIR_NAME_TO_STATUS: dict[str, str] = {v: k for k, v in STATUS_DIR_NAMES.items()}

DEFAULT_LABELS = {
    "feature": ["feature"],
    "sub-feature": ["sub-feature"],
    "task": ["task"],
    "uat": ["user-testing"],
    "bug": ["bug", "sub-feature"],
}

_SLUG_STRIP_PREFIXES = ("[feature]", "[task]", "[uat]", "fix:")


def is_text(ctx: click.Context) -> bool:
    """Check if output mode is human-readable text."""
    return ctx.obj.get("text", False)


def slugify(title: str) -> str:
    """Convert a title to a filesystem-safe slug, max 70 characters."""
    slug = title.lower()
    for prefix in _SLUG_STRIP_PREFIXES:
        slug = slug.replace(prefix, "")
    slug = re.sub(r"[^a-z0-9 ]", " ", slug)
    slug = re.sub(r" +", " ", slug).strip()
    slug = slug.replace(" ", "-")
    if len(slug) > 70:
        slug = slug[:70].rsplit("-", 1)[0]
    return slug or "untitled"


def resolve_scope(issues: dict[str, Issue], children_of: str | None) -> list[str]:
    """Resolve issue slugs in scope, sorted alphabetically."""
    if children_of is not None:
        parent = issues[children_of]
        return sorted(parent.get("children", []))
    return sorted(issues.keys())


def format_issue_line(slug: str, issue: Issue) -> str:
    """Format an issue as a single summary line with labels."""
    labels = issue.get("labels", [])
    line = f"#{slug} [{issue['status']}] {issue['type']}: {issue['title']}"
    if labels:
        line += f" {{{', '.join(labels)}}}"
    return line


def format_full_issue(slug: str, issue: Issue, body: str | None = None) -> dict:
    """Build a complete issue dict for JSON output."""
    obj: dict = {
        "slug": slug,
        "title": issue["title"],
        "type": issue["type"],
        "status": issue["status"],
        "labels": issue.get("labels", []),
        "state": "CLOSED" if issue["status"] == STATUS_DONE else "OPEN",
    }
    if issue["type"] == "feature":
        obj["children"] = issue.get("children", [])
    else:
        obj["parent"] = issue.get("parent")
        obj["dependencies"] = issue.get("dependencies", [])
        obj["agent"] = issue.get("agent")
    if issue.get("closed_reason"):
        obj["closed_reason"] = issue["closed_reason"]
    notes = issue.get("notes", [])
    if notes:
        obj["notes"] = notes
    if body is not None:
        obj["body"] = body
    return obj


def echo_json(data: object) -> None:
    """Output data as formatted JSON."""
    click.echo(json.dumps(data, indent=2))


def log(ctx: click.Context, message: str) -> None:
    """Print a message only in text mode."""
    if is_text(ctx):
        click.echo(message)
