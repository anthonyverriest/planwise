"""Workflow markdown loader."""

from __future__ import annotations

from importlib import resources


WORKFLOW_PACKAGE = "planwise.workflows"


def list_workflows() -> list[str]:
    """Return sorted names of available workflow files without extension."""
    workflow_dir = resources.files(WORKFLOW_PACKAGE)
    return sorted(
        p.name.removesuffix(".md")
        for p in workflow_dir.iterdir()
        if p.name.endswith(".md")
    )


def read_workflow(name: str) -> str | None:
    """Read and return workflow markdown content, or None if not found."""
    ref = resources.files(WORKFLOW_PACKAGE).joinpath(f"{name}.md")
    try:
        return ref.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
