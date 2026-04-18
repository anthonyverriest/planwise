"""Run workflow commands."""

from __future__ import annotations

import click

from planwise.helpers import echo_json, is_text
from planwise.rulesets import parse_rules_callback
from planwise.store import get_store
from planwise.workflows import expand_workflow, list_workflows


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
    arguments = " ".join(arg.removesuffix(".md") for arg in args)
    rule_names = list(rules) if rules else list(get_store(ctx).get_config("rules", []))

    content = expand_workflow(workflow, arguments, rule_names)
    if content is None:
        available = ", ".join(list_workflows())
        raise click.UsageError(
            f"Unknown workflow '{workflow}'. Available: {available}"
        )

    content = content.rstrip() + "\n\n" + WORKFLOW_EPILOGUE

    if is_text(ctx):
        click.echo(content)
    else:
        echo_json({"name": workflow, "content": content})
