"""Candidate detection: find new feature/task issues created during a phase."""

from __future__ import annotations

from planwise.store import MetaStore


def _issue_type(store: MetaStore, slug: str) -> str | None:
    """Return the `type` field of an issue, or None if not readable."""
    result = store.read_issue(slug)
    if result is None:
        return None
    issue, _body = result
    return issue.get("type")


def list_new_candidates(
    before: set[str],
    after: set[str],
    store: MetaStore,
    accepted_types: frozenset[str] = frozenset({"feature", "task"}),
) -> list[tuple[str, str]]:
    """Return [(slug, type), ...] for issues in `after - before` matching `accepted_types`.

    Sorted deterministically by slug for stable output ordering.
    """
    new_slugs = after - before
    candidates: list[tuple[str, str]] = []
    for slug in sorted(new_slugs):
        issue_type = _issue_type(store, slug)
        if issue_type in accepted_types:
            candidates.append((slug, issue_type))
    return candidates
