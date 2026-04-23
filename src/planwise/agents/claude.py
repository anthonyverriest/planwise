"""Claude Code agent integration — CLAUDE.md + .claude/skills + permissions."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import ClassVar

from planwise.agents._instructions import (
    LAYOUT_MARKER,
    PLANNING_MARKER,
    render_instructions,
)
from planwise.agents.base import InstallReport, RenderContext
from planwise.agents.capabilities import Capability
from planwise.agents.render import (
    AskDirective,
    DispatchDirective,
    InvokeDirective,
    SkillRefDirective,
)
from planwise.frontmatter import parse
from planwise.layouts import read_layout
from planwise.workflows import list_workflows, read_workflow

INSTRUCTION_FILE = "CLAUDE.md"

SKILL_TEMPLATE = """\
---
name: {name}
description: "{description}"
---

!`pw pipeline-enter {name} $ARGUMENTS`

!`pw -t run {name} $ARGUMENTS`
"""

NEXT_SKILL_TEMPLATE = """\
---
name: next
description: "Advance to the next phase in the active Planwise pipeline. Run /clear first for fresh context. Pass a slug to pick when multiple candidates exist."
---

!`pw -t pipeline-next $ARGUMENTS`
"""

CLAUDE_PERMISSIONS = [
    "Bash(pw *)",
    "Bash(planwise *)",
    "Bash(grep *)",
    "Bash(cd *)",
    "Bash(ls *)",
    "Bash(wc *)",
]


def _extract_description(workflow_content: str) -> str:
    """Extract the description from workflow YAML frontmatter."""
    meta, _body = parse(workflow_content)
    return meta.get("description", "")


def generate_claude_skills(project_dir: Path) -> list[Path]:
    """Generate .claude/skills/<workflow>/SKILL.md for each workflow plus /next.

    Returns list of created skill directories.
    """
    skills_dir = project_dir / ".claude" / "skills"
    created: list[Path] = []

    for name in list_workflows():
        content = read_workflow(name)
        if content is None:
            continue

        description = _extract_description(content)
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            SKILL_TEMPLATE.format(name=name, description=description),
            encoding="utf-8",
        )
        created.append(skill_dir)

    next_dir = skills_dir / "next"
    next_dir.mkdir(parents=True, exist_ok=True)
    (next_dir / "SKILL.md").write_text(NEXT_SKILL_TEMPLATE, encoding="utf-8")
    created.append(next_dir)

    return created


def remove_claude_skills(project_dir: Path) -> int:
    """Remove all planwise-generated skill directories."""
    skills_dir = project_dir / ".claude" / "skills"
    if not skills_dir.is_dir():
        return 0

    removed = 0
    for name in [*list_workflows(), "next"]:
        skill_dir = skills_dir / name
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir)
            removed += 1

    return removed


def _ensure_claude_permissions(project_dir: Path) -> None:
    """Add pw/planwise Bash permissions to .claude/settings.json."""
    settings_path = project_dir / ".claude" / "settings.json"
    settings: dict = {}

    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))

    allow_list: list[str] = settings.setdefault("permissions", {}).setdefault("allow", [])
    changed = False
    for perm in CLAUDE_PERMISSIONS:
        if perm not in allow_list:
            allow_list.append(perm)
            changed = True

    if changed:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(
            json.dumps(settings, indent=2) + "\n",
            encoding="utf-8",
        )


def _write_instructions(project_dir: Path) -> tuple[Path, bool]:
    """Render CLAUDE.md from the shared Jinja template. Idempotent."""
    target = project_dir / INSTRUCTION_FILE

    if target.exists():
        content = target.read_text(encoding="utf-8")
        if PLANNING_MARKER in content:
            return target, True
        separator = "\n" if content.endswith("\n") else "\n\n"
        rendered = render_instructions(ClaudeAgent.capabilities, layout=None)
        target.write_text(content + separator + rendered, encoding="utf-8")
        return target, False

    target.write_text(render_instructions(ClaudeAgent.capabilities, layout=None), encoding="utf-8")
    return target, False


def _inject_layout(project_dir: Path, layout_name: str) -> tuple[Path, bool]:
    """Splice the named layout into CLAUDE.md before the <output> block."""
    claude_md = project_dir / INSTRUCTION_FILE
    claude_content = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""

    if LAYOUT_MARKER in claude_content:
        return claude_md, True

    layout_content = read_layout(layout_name)
    assert layout_content is not None, f"layout '{layout_name}' validated but missing"
    layout_block = layout_content if layout_content.endswith("\n") else layout_content + "\n"

    from planwise.agents._instructions import OUTPUT_MARKER

    if OUTPUT_MARKER in claude_content:
        head, _, tail = claude_content.partition(OUTPUT_MARKER)
        if not head.endswith("\n\n"):
            head = head.rstrip("\n") + "\n\n"
        new_content = head + layout_block + "\n" + OUTPUT_MARKER + tail
    else:
        separator = "" if not claude_content else ("\n" if claude_content.endswith("\n") else "\n\n")
        new_content = claude_content + separator + layout_block

    claude_md.parent.mkdir(parents=True, exist_ok=True)
    claude_md.write_text(new_content, encoding="utf-8")
    return claude_md, False


class ClaudeAgent:
    """Claude Code target — the reference implementation."""

    name: ClassVar[str] = "claude"
    instruction_file: ClassVar[str] = INSTRUCTION_FILE
    capabilities: ClassVar[frozenset[Capability]] = frozenset(
        {
            Capability.EXECUTABLE_COMMANDS,
            Capability.STRUCTURED_QUESTIONS,
            Capability.NAMED_SUBAGENTS,
            Capability.BUILTIN_EXPLORE,
            Capability.SLASH_INVOKE,
            Capability.SLASH_CHAINING,
            Capability.SETTINGS_FILE,
        }
    )

    def install(self, project_dir: Path, *, layout: str | None = None) -> InstallReport:
        skills = generate_claude_skills(project_dir)
        _ensure_claude_permissions(project_dir)
        path, instr_skipped = _write_instructions(project_dir)
        layout_skipped = False
        if layout is not None:
            _, layout_skipped = _inject_layout(project_dir, layout)
        return InstallReport(
            instruction_file=path,
            instruction_skipped=instr_skipped,
            layout_skipped=layout_skipped,
            skills_created=skills,
        )

    def uninstall(self, project_dir: Path) -> int:
        return remove_claude_skills(project_dir)

    def render_workflow(self, workflow_name: str, body: str) -> str:
        """Expand `{{ ... }}` directives in workflow body for Claude."""
        from planwise.agents.render import render

        return render(body, self, RenderContext(workflow_name=workflow_name))

    def render_ask(self, d: AskDirective, ctx: RenderContext) -> str:
        head = f"Use `AskUserQuestion` tool: **\"{d.prompt}\"**"
        if not d.choices:
            return head
        if all(isinstance(c, list) and len(c) == 2 for c in d.choices):
            bullets = "\n".join(f"- If {label} -> {outcome}" for label, outcome in d.choices)
            return f"{head}\n{bullets}"
        mode = "multi-select" if d.multi_select else "single-select"
        bullets = "\n".join(f"- {c}" for c in d.choices)
        return f"{head}\nChoices ({mode}):\n{bullets}"

    def render_dispatch(self, d: DispatchDirective, ctx: RenderContext) -> str:
        hashes = "#" * d.level
        suffix = f" ({d.detail})" if d.detail else ""
        return f"{hashes} {d.prefix}Dispatch — {d.task}{suffix}"

    def render_invoke(self, d: InvokeDirective, ctx: RenderContext) -> str:
        args = f" {d.args}" if d.args else ""
        return f"/{d.phase}{args}"

    def render_skill_ref(self, d: SkillRefDirective, ctx: RenderContext) -> str:
        return f"`/{d.name}`"

    def render_arguments(self, ctx: RenderContext) -> str:
        return "$ARGUMENTS"
