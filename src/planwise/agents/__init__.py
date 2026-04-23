"""Agent registry and backward-compatible helpers.

The registry maps agent name to concrete `Agent` implementation. Existing
CLI call sites use the module-level helpers (`inject_agent_instructions`,
`inject_layout_section`) — these remain as thin wrappers so Step 1 is a
pure refactor with no behavior change.
"""

from __future__ import annotations

from pathlib import Path

from planwise.agents.base import Agent, InstallReport, RenderContext
from planwise.agents.capabilities import Capability
from planwise.agents.claude import ClaudeAgent
from planwise.agents.cursor import CursorAgent

AGENTS: dict[str, type[Agent]] = {
    ClaudeAgent.name: ClaudeAgent,
    CursorAgent.name: CursorAgent,
}

VALID_AGENTS: tuple[str, ...] = tuple(AGENTS.keys())


def get_agent(name: str) -> Agent:
    """Instantiate a registered agent by name."""
    if name not in AGENTS:
        raise ValueError(f"unknown agent '{name}'; valid: {VALID_AGENTS}")
    return AGENTS[name]()


def inject_agent_instructions(agent: str, project_dir: Path) -> tuple[Path, bool]:
    """Install an agent's skills/subagents/permissions and write instructions.

    Returns (path, already_present). The path points at the agent's primary
    instruction file (CLAUDE.md, .cursor/rules/planwise.mdc, etc.).
    """
    if agent == "claude":
        from planwise.agents.claude import (
            _ensure_claude_permissions,
            _write_instructions,
            generate_claude_skills,
        )

        generate_claude_skills(project_dir)
        _ensure_claude_permissions(project_dir)
        return _write_instructions(project_dir)

    if agent == "cursor":
        instance = CursorAgent()
        report = instance.install(project_dir)
        return report.instruction_file, report.instruction_skipped

    raise ValueError(f"unknown agent '{agent}'")


def inject_layout_section(
    layout_name: str,
    project_dir: Path,
    agent: str = "claude",
) -> tuple[Path, bool]:
    """Splice the named layout into the active agent's instruction file."""
    if agent == "claude":
        from planwise.agents.claude import _inject_layout as _claude_layout

        return _claude_layout(project_dir, layout_name)

    if agent == "cursor":
        from planwise.agents.cursor import _inject_layout as _cursor_layout

        return _cursor_layout(project_dir, layout_name)

    raise ValueError(f"unknown agent '{agent}'")


__all__ = [
    "AGENTS",
    "VALID_AGENTS",
    "Agent",
    "Capability",
    "ClaudeAgent",
    "CursorAgent",
    "InstallReport",
    "RenderContext",
    "get_agent",
    "inject_agent_instructions",
    "inject_layout_section",
]
