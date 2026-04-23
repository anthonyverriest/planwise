"""Golden tests — lock byte-for-byte rendered workflow output per agent."""

from __future__ import annotations

from pathlib import Path

import pytest

from planwise.workflows import expand_workflow

GOLDEN_DIR = Path(__file__).parent / "golden"


@pytest.mark.parametrize(
    ("agent", "workflow", "arguments"),
    [
        (agent, workflow, "<ARGS>")
        for agent in ("claude", "cursor")
        for workflow in (
            "brief",
            "sync",
            "task",
            "optimize",
            "bug",
            "test",
            "implement",
            "memo",
            "plan",
        )
    ],
)
def test_rendered_workflow_matches_golden(agent: str, workflow: str, arguments: str) -> None:
    expected = (GOLDEN_DIR / agent / f"{workflow}.md").read_text(encoding="utf-8")
    actual = expand_workflow(workflow, arguments=arguments, rule_names=None, agent=agent)
    assert actual == expected
