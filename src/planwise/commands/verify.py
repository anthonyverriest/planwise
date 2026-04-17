"""Data integrity verification command."""

from __future__ import annotations

import click

from planwise.frontmatter import parse, to_issue
from planwise.helpers import DIR_NAME_TO_STATUS, STATUS_DIR_NAMES, VALID_STATUSES, echo_json, is_text, slugify
from planwise.store import MetaStore, get_store
from planwise.types import Issue


def register(cli: click.Group) -> None:
    """Register the verify command on the CLI group."""
    cli.add_command(verify)


@click.command()
@click.option("--fix", is_flag=True, help="Auto-fix repairable issues.")
@click.pass_context
def verify(ctx: click.Context, fix: bool) -> None:
    """Check planning data integrity."""
    store = get_store(ctx)
    store.require()

    issues = store.read_all()
    all_errors: list[str] = []

    all_errors.extend(_check_orphaned_references(issues, store, fix))
    all_errors.extend(_check_bidirectional_consistency(issues, store, fix))
    all_errors.extend(_check_dependency_cycles(issues))
    all_errors.extend(_check_frontmatter_integrity(store))
    all_errors.extend(_check_slug_consistency(store))
    all_errors.extend(_check_status_consistency(store))

    if is_text(ctx):
        if all_errors:
            for error in all_errors:
                click.echo(error, err=True)
        else:
            click.echo("All checks passed")
    else:
        echo_json({"passed": len(all_errors) == 0, "errors": all_errors})

    raise SystemExit(0 if not all_errors else 1)


def _check_orphaned_references(
    issues: dict[str, Issue], store: MetaStore, fix: bool
) -> list[str]:
    """Check for references to non-existent issues."""
    errors: list[str] = []
    for slug, issue in issues.items():
        for child in issue.get("children", []):
            if child not in issues:
                errors.append(f"orphaned children: #{child} in #{slug}")
        parent = issue.get("parent")
        if parent is not None and parent not in issues:
            errors.append(f"orphaned parent: #{parent} in #{slug}")
        for dep_entry in issue.get("dependencies", []):
            if dep_entry not in issues:
                errors.append(f"orphaned dependency: #{dep_entry} in #{slug}")

    if errors and fix:
        with store.locked():
            for slug in issues:
                issue, body = store.require_issue(slug)
                changed = False

                children = issue.get("children", [])
                cleaned_children = [c for c in children if c in issues]
                if len(cleaned_children) != len(children):
                    issue["children"] = cleaned_children
                    changed = True

                parent = issue.get("parent")
                if parent is not None and parent not in issues:
                    issue["parent"] = None
                    changed = True

                deps = issue.get("dependencies", [])
                cleaned_deps = [d for d in deps if d in issues]
                if len(cleaned_deps) != len(deps):
                    issue["dependencies"] = cleaned_deps
                    changed = True

                if changed:
                    store.write_issue(slug, issue, body)

        errors.append("auto-fixed: orphaned references removed")

    return errors


def _check_bidirectional_consistency(
    issues: dict[str, Issue], store: MetaStore, fix: bool
) -> list[str]:
    """Check parent-child bidirectional consistency."""
    errors: list[str] = []
    for slug, issue in issues.items():
        parent_slug = issue.get("parent")
        if parent_slug is None:
            continue
        parent = issues.get(parent_slug)
        if parent is None:
            continue
        children = parent.get("children", [])
        if slug not in children:
            errors.append(
                f"parent-child mismatch: #{slug} has parent #{parent_slug} "
                f"but parent children missing #{slug}"
            )

    if errors and fix:
        with store.locked():
            for slug, issue in issues.items():
                parent_slug = issue.get("parent")
                if parent_slug is None:
                    continue
                parent_issue, parent_body = store.require_issue(parent_slug)
                children = parent_issue.get("children", [])
                if slug not in children:
                    children.append(slug)
                    parent_issue["children"] = children
                    store.write_issue(parent_slug, parent_issue, parent_body)
        errors.append("auto-fixed: bidirectional mismatches repaired")

    return errors


def _check_dependency_cycles(issues: dict[str, Issue]) -> list[str]:
    """Check for cycles in the dependency graph using 3-color DFS."""
    UNVISITED, IN_PATH, VISITED = 0, 1, 2
    node_state: dict[str, int] = {}
    cycle_members: set[str] = set()
    current_path: list[str] = []

    def dfs(node: str) -> None:
        node_state[node] = IN_PATH
        current_path.append(node)
        for dep_slug in issues.get(node, {}).get("dependencies", []):
            state = node_state.get(dep_slug, UNVISITED)
            if state == IN_PATH:
                cycle_start = current_path.index(dep_slug)
                cycle_members.update(current_path[cycle_start:])
            elif state == UNVISITED:
                dfs(dep_slug)
        current_path.pop()
        node_state[node] = VISITED

    for slug in issues:
        if node_state.get(slug, UNVISITED) == UNVISITED:
            dfs(slug)

    if not cycle_members:
        return []

    return [f"dependency cycle involving: {', '.join(f'#{s}' for s in sorted(cycle_members))}"]


def _iter_issue_paths(store: MetaStore):
    """Yield all issue file paths across status subdirectories."""
    for status in VALID_STATUSES:
        status_dir = store.issues_dir / STATUS_DIR_NAMES[status]
        if not status_dir.is_dir():
            continue
        for path in sorted(status_dir.glob("*.md")):
            if not path.name.startswith("."):
                yield path


def _check_frontmatter_integrity(store: MetaStore) -> list[str]:
    """Verify each issue file has valid YAML frontmatter."""
    errors: list[str] = []
    for path in _iter_issue_paths(store):
        try:
            text = path.read_text(encoding="utf-8")
            raw, _body = parse(text)
            to_issue(raw)
        except (ValueError, AssertionError, KeyError) as exc:
            errors.append(f"invalid frontmatter in {path.parent.name}/{path.name}: {exc}")
    return errors


def _check_slug_consistency(store: MetaStore) -> list[str]:
    """Verify that each issue's slugified title matches its filename."""
    errors: list[str] = []
    for path in _iter_issue_paths(store):
        try:
            text = path.read_text(encoding="utf-8")
            raw, _body = parse(text)
            issue = to_issue(raw)
        except (ValueError, AssertionError, KeyError):
            continue
        expected_slug = slugify(issue["title"])
        if path.stem != expected_slug:
            errors.append(
                f"slug-title mismatch: {path.parent.name}/{path.name} "
                f"title '{issue['title']}' expects slug '{expected_slug}'"
            )
    return errors


def _check_status_consistency(store: MetaStore) -> list[str]:
    """Verify directory structure and frontmatter-directory status agreement."""
    errors: list[str] = []

    for status in VALID_STATUSES:
        dir_name = STATUS_DIR_NAMES[status]
        status_dir = store.issues_dir / dir_name
        if not status_dir.is_dir():
            errors.append(f"missing status directory: {dir_name}/")

    for path in sorted(store.issues_dir.glob("*.md")):
        if not path.name.startswith("."):
            errors.append(f"issue file outside status directory: {path.name}")

    for path in _iter_issue_paths(store):
        try:
            text = path.read_text(encoding="utf-8")
            raw, _body = parse(text)
            issue = to_issue(raw)
        except (ValueError, AssertionError, KeyError):
            continue
        dir_status = DIR_NAME_TO_STATUS.get(path.parent.name, path.parent.name)
        frontmatter_status = issue["status"]
        if frontmatter_status != dir_status:
            errors.append(
                f"status mismatch: {dir_status}/{path.name} "
                f"frontmatter says '{frontmatter_status}'"
            )
    return errors
