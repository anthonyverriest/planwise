"""Shared instruction-file rendering — single Jinja template, per-agent context.

The template at `agents/_templates/instructions.md.j2` is the single source of
truth for the coding standards embedded in CLAUDE.md / .cursor/rules/planwise.mdc.
Per-agent variance (if any is needed later) lands in the template as
`{% if caps.XXX %}` gates driven by the agent's capability set.
"""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, StrictUndefined

from planwise.agents.capabilities import Capability

PLANNING_MARKER = "<planning>"
LAYOUT_MARKER = "<layout>"
OUTPUT_MARKER = "<output>"

_env = Environment(
    loader=PackageLoader("planwise.agents", "_templates"),
    autoescape=False,
    keep_trailing_newline=True,
    trim_blocks=False,
    lstrip_blocks=False,
    undefined=StrictUndefined,
)


def render_instructions(
    capabilities: frozenset[Capability],
    layout: str | None = None,
) -> str:
    """Render the shared instructions template for a given agent capability set."""
    template = _env.get_template("instructions.md.j2")
    caps = {c.name: (c in capabilities) for c in Capability}
    return template.render(caps=caps, layout=layout)
