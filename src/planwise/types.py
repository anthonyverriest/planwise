"""Domain types for planwise issue tracking."""

from __future__ import annotations

from typing import TypedDict


class Note(TypedDict):
    """Timestamped note attached to an issue."""

    at: str
    text: str


class _IssueRequired(TypedDict):
    """Required fields present on every issue."""

    title: str
    type: str
    status: str
    created: str
    labels: list[str]


class Issue(_IssueRequired, total=False):
    """Complete issue record with optional type-dependent fields."""

    children: list[str]
    parent: str | None
    dependencies: list[str]
    agent: str
    notes: list[Note]
    closed_reason: str
