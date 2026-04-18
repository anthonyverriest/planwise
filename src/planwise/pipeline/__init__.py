"""Pipeline state: /next chains workflow phases via an on-disk state file."""

from __future__ import annotations


PHASE_CHAIN: dict[str, str | None] = {
    "brief": "task",
    "task": None,
    "plan": "implement",
    "implement": "test",
    "test": "optimize",
    "optimize": "memo",
    "memo": None,
}

CREATION_PHASES: dict[str, str] = {
    "plan": "feature",
    "brief": "task",
}

SLUG_CONSUMING_PHASES: frozenset[str] = frozenset(
    {"implement", "test", "optimize", "memo", "task"}
)


__all__ = ["PHASE_CHAIN", "CREATION_PHASES", "SLUG_CONSUMING_PHASES"]
