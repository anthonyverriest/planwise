"""Run workflow commands."""

from __future__ import annotations

import click

from planwise.helpers import echo_json, is_text
from planwise.rulesets import parse_rules_callback
from planwise.store import get_store
from planwise.workflows import expand_workflow, list_workflows


WORKFLOW_EPILOGUE = """\
## Final reconcile and publish

Three guarded steps — each only fires when its precondition holds, so no
empty commits, no silent no-op pushes, no duplication with the workflow body.

### Step 1 — Reconcile workspace with shared backend

```bash
jj workspace update-stale
```

No-op unless another `pw claude` workspace rewrote a change this workspace
touches. Always safe to run.

### Step 2 — Commit trailing working-copy edits (conditional)

Workflows that commit inline (task, implement, test, optimize) usually leave
a clean working copy here. Planning workflows (plan, brief, bug, memo) leave
issue-file or knowledge-file edits from `planwise create` / `planwise status`
that still need committing. Guard so the common case produces no empty change:

```bash
if [ -n "$(jj diff --name-only)" ]; then
  jj commit -m "<type>: <describe trailing edit>"
fi
```

Commit types: feat, fix, ref, test, docs, chore, style. Use imperative mood.

### Step 3 — Fetch and rebase onto trunk

```bash
jj git fetch
jj rebase -d dev@origin
```

Unlike git, jj records rebase conflicts inline as first-class data rather
than aborting. Always check afterwards:

```bash
jj resolve --list
```

If conflicted paths are reported, resolve inline before pushing:

1. Read each conflicted file — jj has materialized `<<<<<<<` / `|||||||` /
   `=======` / `>>>>>>>` markers.
2. Edit the file to produce a coherent unified result. The working copy is
   auto-snapshotted.
3. Confirm `jj resolve --list` reports no remaining conflicts.

### Step 4 — Publish reachable bookmarks (conditional)

Collect every non-trunk bookmark on the stack between `dev@origin` and `@`,
then push them together with `--allow-new` so first-time bookmarks publish
on their initial push. If no eligible bookmark exists, skip with an explicit
message rather than silently no-op:

```bash
BOOKMARKS=$(jj bookmark list -r '::@ ~ ::dev@origin' \\
  --no-graph -T 'name ++ "\\n"' | grep -v '^dev$' | grep -v '^$')

if [ -n "$BOOKMARKS" ]; then
  ARGS=""
  for b in $BOOKMARKS; do ARGS="$ARGS --bookmark $b"; done
  jj git push --allow-new $ARGS
else
  echo "No local bookmark on this stack — commits stay local. Create a bookmark to publish."
fi
```

jj auto-snapshots the working copy — no staging area. The colocated git repo
stays in sync, so CI and the remote see conventional git commits.
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
