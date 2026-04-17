"""Run workflow commands."""

from __future__ import annotations

import click

from planwise.helpers import echo_json, is_text
from planwise.rulesets import parse_rules_callback, read_ruleset
from planwise.store import get_store
from planwise.workflows import list_workflows, read_workflow

RULES_MARKER = "$RULES"
TEST_RULES_MARKER = "$TESTRULES"
RULE_MARKERS: dict[str, str] = {
    RULES_MARKER: "base",
    TEST_RULES_MARKER: "test-base",
}


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


def _replace_rules(ctx: click.Context, content: str, overrides: tuple[str, ...]) -> str:
    """Replace each rule marker with its base + project/override ruleset content."""
    if not any(marker in content for marker in RULE_MARKERS):
        return content

    names: list[str] = list(overrides) if overrides else get_store(ctx).get_config("rules", [])
    for marker, base_name in RULE_MARKERS.items():
        if marker not in content:
            continue
        replacement = _expand_marker(base_name, names) if names else ""
        content = content.replace(marker, replacement)
    return content


WORKFLOW_EPILOGUE = """\
## Final commit

After completing all steps, commit any remaining changes (including issue status moves):

```bash
git add -A
git commit -m "<type>: <describe what changed>"
# Commit types: feat, fix, ref, test, docs, chore, style
git pull --rebase origin dev
git push
```
"""


def register(cli: click.Group) -> None:
    """Register the run command on the CLI group."""
    cli.add_command(run)


@click.command()
@click.argument("workflow", required=False, default=None)
@click.argument("args", nargs=-1)
@click.option("--list", "list_flag", is_flag=True, help="List available workflows.")
@click.option(
    "--rules",
    "rules",
    multiple=True,
    callback=parse_rules_callback,
    is_eager=True,
    expose_value=True,
    help="Override project rulesets for this run (comma-separated or repeatable).",
)
@click.pass_context
def run(
    ctx: click.Context,
    workflow: str | None,
    args: tuple[str, ...],
    list_flag: bool,
    rules: tuple[str, ...],
) -> None:
    """Output a workflow's markdown content.

    Extra arguments after the workflow name replace $ARGUMENTS in the template.
    """
    if list_flag:
        names = list_workflows()
        if is_text(ctx):
            for name in names:
                click.echo(name)
        else:
            echo_json(names)
        return

    if not workflow:
        raise click.UsageError(
            "Provide a workflow name, or use --list to see available workflows."
        )

    workflow = workflow.removesuffix(".md")
    content = read_workflow(workflow)
    if content is None:
        available = ", ".join(list_workflows())
        raise click.UsageError(
            f"Unknown workflow '{workflow}'. Available: {available}"
        )

    arguments = " ".join(arg.removesuffix(".md") for arg in args)
    content = content.replace("$ARGUMENTS", arguments)
    content = _replace_rules(ctx, content, rules)
    content = content.rstrip() + "\n\n" + WORKFLOW_EPILOGUE

    if is_text(ctx):
        click.echo(content)
    else:
        echo_json({"name": workflow, "content": content})
