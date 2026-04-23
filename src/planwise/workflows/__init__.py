"""Workflow markdown loader and template expansion."""

from __future__ import annotations

from importlib import resources

from planwise.rulesets import read_ruleset


WORKFLOW_PACKAGE = "planwise.workflows"

RULES_MARKER = "$RULES"
TEST_RULES_MARKER = "$TESTRULES"
ARGUMENTS_MARKER = "$ARGUMENTS"

_RULE_MARKERS: dict[str, str] = {
    RULES_MARKER: "base",
    TEST_RULES_MARKER: "test-base",
}


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


def _expand_marker(base_name: str, project_names: list[str]) -> str:
    """Build a marker's replacement: base ruleset followed by project rulesets."""
    sections: list[str] = []
    base = read_ruleset(base_name)
    if base is not None:
        sections.append(base.strip())

    for name in project_names:
        if name == base_name:
            continue
        ruleset = read_ruleset(name)
        if ruleset is not None:
            sections.append(ruleset.strip())

    return "\n\n".join(sections) if sections else ""


def _replace_rules(content: str, rule_names: list[str]) -> str:
    """Replace each rule marker with its base + project ruleset content."""
    if not any(marker in content for marker in _RULE_MARKERS):
        return content

    for marker, base_name in _RULE_MARKERS.items():
        if marker not in content:
            continue
        replacement = _expand_marker(base_name, rule_names) if rule_names else ""
        content = content.replace(marker, replacement)
    return content


def expand_workflow(
    name: str,
    arguments: str = "",
    rule_names: list[str] | None = None,
    agent: str = "claude",
) -> str | None:
    """Load a workflow, expand directives for `agent`, substitute markers.

    Args:
        name: Workflow name without the .md extension.
        arguments: Value to substitute for $ARGUMENTS markers.
        rule_names: Project ruleset names appended after the base ruleset when
            expanding $RULES / $TESTRULES. Empty/None removes the markers.
        agent: Target agent for directive rendering. Defaults to "claude".

    Returns:
        The expanded workflow text, or None if the workflow does not exist.
    """
    from planwise.agents import get_agent

    content = read_workflow(name)
    if content is None:
        return None
    renderer = get_agent(agent)
    content = renderer.render_workflow(name, content)
    content = content.replace(ARGUMENTS_MARKER, arguments)
    content = _replace_rules(content, list(rule_names) if rule_names else [])
    return content
