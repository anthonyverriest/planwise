"""Ruleset loader — lists and reads bundled ruleset markdown files."""

from __future__ import annotations

from importlib import resources

import click

RULESET_PACKAGE = "planwise.rulesets"
AUTO_INJECTED_RULESETS = frozenset({"base", "test-base"})


def list_rulesets() -> list[str]:
    """Return sorted names of available ruleset files, excluding auto-injected bases."""
    ruleset_dir = resources.files(RULESET_PACKAGE)
    return sorted(
        name for name in (
            p.name.removesuffix(".md")
            for p in ruleset_dir.iterdir()
            if p.name.endswith(".md")
        )
        if name not in AUTO_INJECTED_RULESETS
    )


def read_ruleset(name: str) -> str | None:
    """Read and return ruleset markdown content, or None if not found."""
    ref = resources.files(RULESET_PACKAGE).joinpath(f"{name}.md")
    try:
        return ref.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


_AVAILABLE_RULESETS = set(list_rulesets())


def parse_rules_callback(
    _ctx: click.Context, _param: click.Parameter, values: tuple[str, ...]
) -> tuple[str, ...]:
    """Click callback: split comma-separated ruleset names and validate each."""
    names: list[str] = []
    for value in values:
        for name in value.split(","):
            name = name.strip()
            if name not in _AVAILABLE_RULESETS:
                available = ", ".join(sorted(_AVAILABLE_RULESETS))
                raise click.BadParameter(f"'{name}' is not a valid ruleset. Available: {available}")
            names.append(name)
    return tuple(names)
