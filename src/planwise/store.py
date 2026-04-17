"""MetaStore: per-issue file operations for the planning directory."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import click
from filelock import FileLock

from planwise.frontmatter import from_issue, parse, serialize, to_issue
from planwise.helpers import DIR_NAME_TO_STATUS, STATUS_DIR_NAMES, VALID_STATUSES, slugify
from planwise.types import Issue


def get_planning_dir() -> Path:
    """Resolve the planning directory from PLANWISE_DIR env var or cwd."""
    env = os.environ.get("PLANWISE_DIR")
    if env:
        return Path(env)
    return Path.cwd() / "planwise"


def get_store(ctx: click.Context) -> MetaStore:
    """Retrieve the MetaStore from the Click context."""
    return ctx.obj["store"]


class MetaStore:
    """Per-issue file storage with file locking for the planning directory."""

    def __init__(self, planning_dir: Path | None = None):
        self.planning_dir = planning_dir or get_planning_dir()
        self.issues_dir = self.planning_dir / "issues"
        self.lock_path = self.planning_dir / ".lock"
        self.config_path = self.planning_dir / "config.json"

    def require(self) -> None:
        """Validate that the planning directory and issues subdirectory exist."""
        if not self.planning_dir.is_dir():
            raise click.UsageError(
                f"Planning dir not found: {self.planning_dir}. Run: planwise init"
            )
        if not self.issues_dir.is_dir():
            raise click.UsageError(
                f"Issues dir not found: {self.issues_dir}. Run: planwise init"
            )

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Acquire the file lock as a context manager."""
        lock = FileLock(self.lock_path)
        with lock:
            yield

    def read_all(self) -> dict[str, Issue]:
        """Scan all issue files across status directories, indexed by slug."""
        results: dict[str, Issue] = {}
        for status in VALID_STATUSES:
            dir_name = STATUS_DIR_NAMES[status]
            status_dir = self.issues_dir / dir_name
            if not status_dir.is_dir():
                continue
            for path in sorted(status_dir.glob("*.md")):
                if path.name.startswith("."):
                    continue
                text = path.read_text(encoding="utf-8")
                raw, _body = parse(text)
                issue = to_issue(raw)
                issue["status"] = status
                results[path.stem] = issue
        return results

    def read_issue(self, slug: str) -> tuple[Issue, str] | None:
        """Read one issue file, returning (metadata, body) or None."""
        path = self._find_path(slug)
        if path is None:
            return None
        text = path.read_text(encoding="utf-8")
        raw, body = parse(text)
        issue = to_issue(raw)
        issue["status"] = DIR_NAME_TO_STATUS.get(path.parent.name, path.parent.name)
        return issue, body

    def require_issue(self, slug: str) -> tuple[Issue, str]:
        """Read one issue file, raising UsageError if not found."""
        result = self.read_issue(slug)
        if result is None:
            raise click.UsageError(f"Issue #{slug} not found")
        return result

    def write_issue(self, slug: str, issue: Issue, body: str) -> None:
        """Atomically write an issue file, moving between status dirs if needed."""
        target_dir = self.issues_dir / STATUS_DIR_NAMES[issue["status"]]
        target_dir.mkdir(exist_ok=True)
        target_path = target_dir / f"{slug}.md"

        old_path = self._find_path(slug)

        metadata = from_issue(issue)
        text = serialize(metadata, body)

        tmp = target_path.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target_path)

        if old_path is not None and old_path != target_path:
            old_path.unlink(missing_ok=True)

    def slug_exists(self, slug: str) -> bool:
        """Check if an issue file exists for the given slug."""
        return self._find_path(slug) is not None

    def list_slugs(self) -> list[str]:
        """List all issue slugs for completion support."""
        slugs: list[str] = []
        for status in VALID_STATUSES:
            status_dir = self.issues_dir / STATUS_DIR_NAMES[status]
            if not status_dir.is_dir():
                continue
            for path in sorted(status_dir.glob("*.md")):
                if not path.name.startswith("."):
                    slugs.append(path.stem)
        return sorted(slugs)

    def rename_issue(self, old_slug: str, new_slug: str) -> None:
        """Rename an issue file and update all references across issue files."""
        old_path = self._find_path(old_slug)
        if old_path is not None:
            new_path = old_path.parent / f"{new_slug}.md"
            old_path.rename(new_path)

        for status in VALID_STATUSES:
            status_dir = self.issues_dir / STATUS_DIR_NAMES[status]
            if not status_dir.is_dir():
                continue
            for path in sorted(status_dir.glob("*.md")):
                if path.name.startswith("."):
                    continue
                text = path.read_text(encoding="utf-8")
                raw, file_body = parse(text)
                changed = False

                if raw.get("parent") == old_slug:
                    raw["parent"] = new_slug
                    changed = True
                if "children" in raw:
                    children = raw["children"]
                    if old_slug in children:
                        raw["children"] = [new_slug if c == old_slug else c for c in children]
                        changed = True
                if "dependencies" in raw:
                    deps = raw["dependencies"]
                    if old_slug in deps:
                        raw["dependencies"] = [new_slug if d == old_slug else d for d in deps]
                        changed = True

                if changed:
                    updated_text = serialize(raw, file_body)
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(updated_text, encoding="utf-8")
                    os.replace(tmp, path)

    def _find_path(self, slug: str) -> Path | None:
        """Find the file for an issue slug by scanning status directories."""
        for status in VALID_STATUSES:
            candidate = self.issues_dir / STATUS_DIR_NAMES[status] / f"{slug}.md"
            if candidate.is_file():
                return candidate
        return None

    def get_config(self, key: str, default: object = None) -> object:
        """Read a value from config.json, returning default if missing."""
        if self.config_path.is_file():
            config = json.loads(self.config_path.read_text(encoding="utf-8"))
            return config.get(key, default)
        return default
