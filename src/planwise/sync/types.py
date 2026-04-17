"""Domain types for the sync pipeline framework."""

from __future__ import annotations

from typing import Literal, TypedDict


StepStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "fixed",
    "fix_attempted",
    "skipped",
]

GateType = Literal["auto", "human"]

DEFAULT_TIMEOUT_SECONDS = 300
MAX_STORED_OUTPUT_LINES = 200


class FailurePattern(TypedDict):
    """A known failure with regex match and optional fix command."""

    pattern: str
    message: str
    fix: str


class _PluginActionRequired(TypedDict):
    """Required fields for a plugin action."""

    command: str


class PluginAction(_PluginActionRequired, total=False):
    """A named action provided by a plugin."""

    success_pattern: str
    failure_patterns: list[FailurePattern]
    context: str
    timeout: int


class Plugin(TypedDict):
    """A loaded plugin definition."""

    name: str
    description: str
    actions: dict[str, PluginAction]


class _PipelineStepRequired(TypedDict):
    """Required fields for a pipeline step."""

    name: str


class PipelineStep(_PipelineStepRequired, total=False):
    """A single step in the sync pipeline."""

    plugin: str
    action: str
    gate: GateType
    params: dict[str, str]
    run: str


class PipelineConfig(TypedDict):
    """Top-level pipeline configuration."""

    name: str
    description: str
    steps: list[PipelineStep]
    plugin_dirs: list[str]


class StepResult(TypedDict, total=False):
    """Execution result for a single step."""

    step_name: str
    status: StepStatus
    exit_code: int
    stdout: str
    stderr: str
    started_at: str
    finished_at: str
    matched_failure: str
    fix_command: str
    fix_stdout: str
    plugin_context: str


class SyncState(TypedDict):
    """Persisted state of a sync run."""

    pipeline_name: str
    started_at: str
    updated_at: str
    current_step: int
    steps: list[StepResult]
    completed: bool
