"""Click custom parameter type with shell tab completion for issue slugs."""

from __future__ import annotations

import click
from click.shell_completion import CompletionItem

from planwise.store import MetaStore


class IssueSlug(click.ParamType):
    """Click parameter type that validates and completes issue slugs."""

    name = "slug"

    def convert(
        self, value: str, param: click.Parameter | None, ctx: click.Context | None
    ) -> str:
        """Validate that the slug references an existing issue."""
        if ctx is None or ctx.obj is None:
            return value
        store: MetaStore = ctx.obj["store"]
        if not store.slug_exists(value):
            self.fail(f"Issue #{value} not found", param, ctx)
        return value

    def shell_complete(
        self, ctx: click.Context, param: click.Parameter, incomplete: str
    ) -> list[CompletionItem]:
        """Complete to existing issue slugs with titles as help text."""
        store = MetaStore()
        try:
            store.require()
            issues = store.read_all()
        except (click.UsageError, FileNotFoundError, ValueError):
            return []
        return [
            CompletionItem(slug, help=issue["title"])
            for slug, issue in sorted(issues.items())
            if slug.startswith(incomplete)
        ]
