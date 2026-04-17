"""Layout loader — lists and reads bundled package-layout markdown files."""

from __future__ import annotations

from importlib import resources

import click

LAYOUT_PACKAGE = "planwise.layouts"


def list_layouts() -> list[str]:
    """Return sorted names of available layout preset files."""
    layout_dir = resources.files(LAYOUT_PACKAGE)
    return sorted(
        p.name.removesuffix(".md")
        for p in layout_dir.iterdir()
        if p.name.endswith(".md")
    )


def read_layout(name: str) -> str | None:
    """Read and return layout markdown content, or None if not found."""
    ref = resources.files(LAYOUT_PACKAGE).joinpath(f"{name}.md")
    try:
        return ref.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


_AVAILABLE_LAYOUTS = set(list_layouts())


def validate_layout_callback(
    _ctx: click.Context, _param: click.Parameter, value: str | None
) -> str | None:
    """Click callback: validate a single layout name against bundled layouts."""
    if value is None:
        return None
    if value not in _AVAILABLE_LAYOUTS:
        available = ", ".join(sorted(_AVAILABLE_LAYOUTS))
        raise click.BadParameter(f"'{value}' is not a valid layout. Available: {available}")
    return value
