"""Candidate resolution: find the most recently created advanceable issue."""

from __future__ import annotations

from planwise.store import MetaStore


_ADVANCEABLE_TYPES: frozenset[str] = frozenset({"feature", "task", "bug"})
_CANDIDATE_STATUS: str = "ready"


def find_latest_creation_candidate(store: MetaStore) -> str | None:
    """Return the slug of the most recently created `ready` feature/task/bug, or None.

    Used by `/next` when no slug is given and no slug-consuming pipeline is in flight —
    it resolves to "whatever the user most recently planned/briefed/triaged."
    """
    issues = store.read_all()
    candidates: list[tuple[str, str]] = []
    for slug, issue in issues.items():
        if issue.get("type") not in _ADVANCEABLE_TYPES:
            continue
        if issue.get("status") != _CANDIDATE_STATUS:
            continue
        created = issue.get("created", "")
        candidates.append((created, slug))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]
