"""YAML frontmatter parsing and serialization for issue markdown files."""

from __future__ import annotations

from datetime import date

import yaml

from planwise.types import Issue

_KEY_ORDER = [
    "title", "type", "status", "created", "labels",
    "parent", "children", "dependencies", "agent", "notes", "closed_reason",
]

_OPTIONAL_LIST_FIELDS = {"children", "dependencies", "notes", "labels"}
_OPTIONAL_SCALAR_FIELDS = {"parent", "agent", "closed_reason"}


def parse(text: str) -> tuple[dict, str]:
    """Parse a markdown file with YAML frontmatter into (metadata, body).

    Raises ValueError if frontmatter delimiters are missing or malformed.
    """
    if not text.startswith("---"):
        raise ValueError("Missing opening frontmatter delimiter")

    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("Missing closing frontmatter delimiter")

    yaml_text = text[4:end]
    body_start = end + 4
    body = text[body_start:].lstrip("\n")

    raw = yaml.safe_load(yaml_text)
    if not isinstance(raw, dict):
        raise ValueError("Frontmatter is not a YAML mapping")

    return raw, body


def serialize(metadata: dict, body: str) -> str:
    """Serialize metadata and body into a markdown file with YAML frontmatter."""
    ordered = _order_keys(metadata)
    yaml_text = yaml.dump(
        ordered,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    result = f"---\n{yaml_text}---\n"
    if body:
        result += f"\n{body}"
    if not result.endswith("\n"):
        result += "\n"
    return result


def to_issue(raw: dict) -> Issue:
    """Convert a raw frontmatter dict to a typed Issue.

    Handles pyyaml's date coercion (datetime.date -> str) and type validation.
    """
    assert "title" in raw, "Missing required field: title"
    assert "type" in raw, "Missing required field: type"
    assert "status" in raw, "Missing required field: status"
    assert "created" in raw, "Missing required field: created"

    issue: dict = {
        "title": str(raw["title"]),
        "type": str(raw["type"]),
        "status": str(raw["status"]),
        "created": _coerce_date(raw["created"]),
        "labels": list(raw.get("labels", [])),
    }

    if "children" in raw and raw["children"]:
        issue["children"] = [str(c) for c in raw["children"]]
    if "parent" in raw and raw["parent"] is not None:
        issue["parent"] = str(raw["parent"])
    if "dependencies" in raw and raw["dependencies"]:
        issue["dependencies"] = [str(d) for d in raw["dependencies"]]
    if "agent" in raw and raw["agent"] is not None:
        issue["agent"] = str(raw["agent"])
    if "notes" in raw and raw["notes"]:
        issue["notes"] = [
            {"at": _coerce_date(n["at"]), "text": str(n["text"])}
            for n in raw["notes"]
        ]
    if "closed_reason" in raw and raw["closed_reason"] is not None:
        issue["closed_reason"] = str(raw["closed_reason"])

    return issue


def from_issue(issue: Issue) -> dict:
    """Convert an Issue to a frontmatter-ready dict, omitting empty optionals."""
    result: dict = {}
    for key in _KEY_ORDER:
        if key not in issue:
            continue
        value = issue[key]
        if key in _OPTIONAL_LIST_FIELDS and not value:
            continue
        if key in _OPTIONAL_SCALAR_FIELDS and value is None:
            continue
        result[key] = value
    return result


def _order_keys(metadata: dict) -> dict:
    """Return a new dict with keys ordered per _KEY_ORDER."""
    ordered: dict = {}
    for key in _KEY_ORDER:
        if key in metadata:
            ordered[key] = metadata[key]
    for key in metadata:
        if key not in ordered:
            ordered[key] = metadata[key]
    return ordered


def _coerce_date(value: object) -> str:
    """Convert pyyaml date objects back to ISO format strings."""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
