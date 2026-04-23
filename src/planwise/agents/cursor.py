"""Cursor agent integration — .cursor/rules/planwise.mdc + per-workflow subagents.

Cursor renders directives differently from Claude in three places:
- `{{ ask }}` — no stable AskUserQuestion analog; falls back to "AskQuestion if
  available; otherwise ask in chat".
- `{{ dispatch agent="general-purpose" }}` — routed through the installed
  `planwise-worker` subagent (Cursor has no built-in general-purpose dispatch).
- `{{ invoke phase=... }}` — same `/phase args` form (Cursor subagents are
  slash-invokable), but the phase subagent is installed via this agent.

Dispatch heading rendering and `skill_ref` match Claude — the markdown heading
reads naturally regardless of backend.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import ClassVar

from planwise.agents._instructions import (
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
    render,
)
from planwise.frontmatter import parse
from planwise.layouts import read_layout
from planwise.workflows import list_workflows, read_workflow

INSTRUCTION_FILE = ".cursor/rules/planwise.mdc"
AGENTS_DIR = ".cursor/agents"

RULES_FRONTMATTER = """\
---
description: Planwise coding standards and planning conventions
globs: "**"
alwaysApply: true
---

"""

SUBAGENT_TEMPLATE = """\
---
name: {name}
description: "{description}"
model: inherit
readonly: false
is_background: false
---

{body}
"""

WORKFLOW_SHIM_BODY = """\
Run the Planwise `{name}` workflow.

The workflow body is fetched from Planwise at run time so it always reflects
the current version. Execute these two shell steps in order, then follow the
output of step 2 as your workflow for the rest of this conversation.

1. Dispatch the Bash subagent to run:

   ```
   pw pipeline-enter {name} "$TASK"
   ```

   where `$TASK` is the user's message to this subagent (may be empty). This
   records that the `{name}` workflow has started.

2. Dispatch the Bash subagent to run:

   ```
   pw -t run --agent cursor {name} "$TASK"
   ```

   The stdout is the fully-rendered workflow markdown for Cursor — all
   Planwise directives are already expanded. Follow it verbatim until the
   workflow is complete.
"""

NEXT_SUBAGENT_BODY = """\
Advance to the next phase in the active Planwise pipeline.

Dispatch the Bash subagent to run:

```
pw -t pipeline-next --agent cursor "$TASK"
```

where `$TASK` is the optional slug passed by the user (empty to auto-pick the
most recently active pipeline). The stdout is the next phase's workflow body
rendered for Cursor — follow it exactly for the rest of this conversation.
Consider starting a fresh chat first so context stays focused.
"""

WORKER_SUBAGENT_NAME = "planwise-worker"
WORKER_SUBAGENT_BODY = """\
General-purpose Planwise worker subagent.

Invoked by workflow `dispatch` blocks that previously targeted a Claude
`general-purpose` subagent. Read the protocol file the dispatch points at,
execute it against the inputs the main thread provides, and return the
structured result the protocol specifies. Do not modify files unless the
protocol explicitly requests it.
"""


def _extract_description(workflow_content: str) -> str:
    meta, _body = parse(workflow_content)
    return meta.get("description", "")


def _subagent_description(name: str, workflow_description: str) -> str:
    if workflow_description:
        return workflow_description.replace('"', '\\"')
    return f"Planwise {name} workflow"


def _inject_layout(project_dir: Path, layout_name: str) -> tuple[Path, bool]:
    """Splice the named layout into .cursor/rules/planwise.mdc before <output>."""
    from planwise.agents._instructions import LAYOUT_MARKER, OUTPUT_MARKER

    target = project_dir / INSTRUCTION_FILE
    content = target.read_text(encoding="utf-8") if target.exists() else ""

    if LAYOUT_MARKER in content:
        return target, True

    layout_content = read_layout(layout_name)
    assert layout_content is not None, f"layout '{layout_name}' validated but missing"
    layout_block = layout_content if layout_content.endswith("\n") else layout_content + "\n"

    if OUTPUT_MARKER in content:
        head, _, tail = content.partition(OUTPUT_MARKER)
        if not head.endswith("\n\n"):
            head = head.rstrip("\n") + "\n\n"
        new_content = head + layout_block + "\n" + OUTPUT_MARKER + tail
    else:
        separator = "" if not content else ("\n" if content.endswith("\n") else "\n\n")
        new_content = content + separator + layout_block

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content, encoding="utf-8")
    return target, False


def _write_rules_file(project_dir: Path, layout: str | None) -> tuple[Path, bool]:
    """Write .cursor/rules/planwise.mdc with coding standards (+ optional layout)."""
    target = project_dir / INSTRUCTION_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        content = target.read_text(encoding="utf-8")
        if PLANNING_MARKER in content:
            return target, True

    layout_block: str | None = None
    if layout is not None:
        layout_content = read_layout(layout)
        assert layout_content is not None, f"layout '{layout}' validated but missing"
        layout_block = layout_content

    body = render_instructions(CursorAgent.capabilities, layout=layout_block)
    target.write_text(RULES_FRONTMATTER + body, encoding="utf-8")
    return target, False


def generate_cursor_subagents(project_dir: Path, agent: "CursorAgent") -> list[Path]:
    """Emit one .cursor/agents/<workflow>.md per workflow, plus `next` + worker.

    Workflow subagents are thin shell shims that call `pw pipeline-enter` +
    `pw -t run --agent cursor` at invocation time, so workflow edits land in
    installed projects without a regen.
    """
    agents_dir = project_dir / AGENTS_DIR
    agents_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for name in list_workflows():
        content = read_workflow(name)
        if content is None:
            continue
        description = _subagent_description(name, _extract_description(content))
        body = WORKFLOW_SHIM_BODY.format(name=name)
        subagent = agents_dir / f"{name}.md"
        subagent.write_text(
            SUBAGENT_TEMPLATE.format(name=name, description=description, body=body),
            encoding="utf-8",
        )
        created.append(subagent)

    next_file = agents_dir / "next.md"
    next_file.write_text(
        SUBAGENT_TEMPLATE.format(
            name="next",
            description="Advance to the next phase in the active Planwise pipeline.",
            body=NEXT_SUBAGENT_BODY,
        ),
        encoding="utf-8",
    )
    created.append(next_file)

    worker_file = agents_dir / f"{WORKER_SUBAGENT_NAME}.md"
    worker_file.write_text(
        SUBAGENT_TEMPLATE.format(
            name=WORKER_SUBAGENT_NAME,
            description="General-purpose Planwise worker for workflow dispatch blocks.",
            body=WORKER_SUBAGENT_BODY,
        ),
        encoding="utf-8",
    )
    created.append(worker_file)

    return created


def remove_cursor_subagents(project_dir: Path) -> int:
    """Remove .cursor/agents/ subagent files written by Planwise."""
    agents_dir = project_dir / AGENTS_DIR
    if not agents_dir.is_dir():
        return 0
    removed = 0
    for name in [*list_workflows(), "next", WORKER_SUBAGENT_NAME]:
        target = agents_dir / f"{name}.md"
        if target.is_file():
            target.unlink()
            removed += 1
    try:
        next(agents_dir.iterdir())
    except StopIteration:
        shutil.rmtree(agents_dir)
    return removed


class CursorAgent:
    """Cursor target — structured subagents + MDC rules file."""

    name: ClassVar[str] = "cursor"
    instruction_file: ClassVar[str] = INSTRUCTION_FILE
    capabilities: ClassVar[frozenset[Capability]] = frozenset(
        {
            Capability.NAMED_SUBAGENTS,
            Capability.BUILTIN_EXPLORE,
            Capability.SLASH_INVOKE,
        }
    )

    def install(self, project_dir: Path, *, layout: str | None = None) -> InstallReport:
        path, instr_skipped = _write_rules_file(project_dir, layout)
        subagents = generate_cursor_subagents(project_dir, self)
        return InstallReport(
            instruction_file=path,
            instruction_skipped=instr_skipped,
            layout_skipped=False,
            skills_created=subagents,
        )

    def uninstall(self, project_dir: Path) -> int:
        return remove_cursor_subagents(project_dir)

    def render_workflow(self, workflow_name: str, body: str) -> str:
        return render(body, self, RenderContext(workflow_name=workflow_name))

    def render_ask(self, d: AskDirective, ctx: RenderContext) -> str:
        head = f"Use `AskQuestion` if available (fallback: ask in chat): **\"{d.prompt}\"**"
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
        if d.detail is None:
            return f"{hashes} {d.prefix}Dispatch — {d.task}"
        detail = d.detail.replace("general-purpose", WORKER_SUBAGENT_NAME)
        return f"{hashes} {d.prefix}Dispatch — {d.task} ({detail})"

    def render_invoke(self, d: InvokeDirective, ctx: RenderContext) -> str:
        args = f" {d.args}" if d.args else ""
        return f"/{d.phase}{args}"

    def render_skill_ref(self, d: SkillRefDirective, ctx: RenderContext) -> str:
        return f"`/{d.name}`"

    def render_arguments(self, ctx: RenderContext) -> str:
        return "<the user's task>"
