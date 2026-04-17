"""Step execution engine: run commands, match failure patterns, attempt fixes."""

from __future__ import annotations

import re
import subprocess

from planwise.sync import now_iso as _now_iso
from planwise.sync.errors import StepTimeoutError
from planwise.sync.types import (
    DEFAULT_TIMEOUT_SECONDS,
    FailurePattern,
    PipelineStep,
    Plugin,
    PluginAction,
    StepResult,
)


def _resolve_command(template: str, params: dict[str, str]) -> str:
    """Substitute placeholders in a command template.

    Raises ValueError if unresolved placeholders remain.
    """
    resolved = template.format_map(params)
    unresolved = re.findall(r"\{(\w+)\}", resolved)
    if unresolved:
        raise ValueError(
            f"Unresolved placeholders in command: {', '.join(unresolved)}. "
            f"Available params: {', '.join(sorted(params))}"
        )
    return resolved


def _run_command(command: str, timeout: int) -> tuple[int, str, str]:
    """Execute a shell command and return (exit_code, stdout, stderr).

    Raises StepTimeoutError if the command exceeds the timeout.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise StepTimeoutError(
            f"Command timed out after {timeout}s: {command}"
        ) from exc
    return result.returncode, result.stdout, result.stderr


def _check_success(exit_code: int, combined_output: str, action: PluginAction) -> bool:
    """Determine if a command execution was successful.

    When a success_pattern is defined, a match overrides a non-zero exit code.
    This handles tools like `terraform plan -detailed-exitcode` where exit code 2
    means "changes pending" (expected success, not failure).
    """
    success_pattern = action.get("success_pattern")
    if success_pattern is not None and re.search(success_pattern, combined_output, re.MULTILINE):
        return True
    return exit_code == 0


def _match_failure(
    combined_output: str, failure_patterns: list[FailurePattern]
) -> FailurePattern | None:
    """Find the first matching failure pattern, or None."""
    for fp in failure_patterns:
        if re.search(fp["pattern"], combined_output, re.MULTILINE | re.DOTALL):
            return fp
    return None


def _resolve_action(step: PipelineStep, plugins: dict[str, Plugin]) -> tuple[str, PluginAction | None]:
    """Resolve the command and plugin action for a step.

    Returns (resolved_command, plugin_action_or_none).
    """
    inline_command = step.get("run")
    if inline_command:
        return inline_command, None

    plugin_name = step["plugin"]
    action_name = step["action"]
    plugin = plugins[plugin_name]
    action = plugin["actions"][action_name]
    params = step.get("params", {})
    command = _resolve_command(action["command"], params)
    return command, action


def execute_step(step: PipelineStep, plugins: dict[str, Plugin]) -> StepResult:
    """Execute a single pipeline step: run command, match patterns, attempt fix.

    This function handles the full execution lifecycle for one step:
    1. Resolve the command from plugin action or inline run
    2. Execute the command
    3. Check success via exit code and optional success_pattern
    4. On failure, match against known failure patterns
    5. If a fix command exists, attempt it and re-run
    6. Return structured result for the orchestrator
    """
    started_at = _now_iso()
    result = StepResult(step_name=step["name"], status="running", started_at=started_at)

    command, action = _resolve_action(step, plugins)

    timeout = DEFAULT_TIMEOUT_SECONDS
    if action and "timeout" in action:
        timeout = action["timeout"]

    try:
        exit_code, stdout, stderr = _run_command(command, timeout)
    except StepTimeoutError:
        result["status"] = "failed"
        result["stderr"] = f"Command timed out after {timeout}s"
        result["finished_at"] = _now_iso()
        return result

    result["exit_code"] = exit_code
    result["stdout"] = stdout
    result["stderr"] = stderr

    combined = stdout + "\n" + stderr

    if action is None:
        result["status"] = "success" if exit_code == 0 else "failed"
        result["finished_at"] = _now_iso()
        return result

    if _check_success(exit_code, combined, action):
        result["status"] = "success"
        result["finished_at"] = _now_iso()
        return result

    plugin_context = action.get("context", "")
    if plugin_context:
        result["plugin_context"] = plugin_context

    failure_patterns = action.get("failure_patterns", [])
    matched = _match_failure(combined, failure_patterns)

    if matched is None:
        result["status"] = "failed"
        result["finished_at"] = _now_iso()
        return result

    result["matched_failure"] = matched["message"]

    if not matched["fix"]:
        result["status"] = "failed"
        result["finished_at"] = _now_iso()
        return result

    params = step.get("params", {})
    try:
        fix_command = _resolve_command(matched["fix"], params)
    except ValueError:
        result["status"] = "failed"
        result["finished_at"] = _now_iso()
        return result

    result["fix_command"] = fix_command

    try:
        _fix_code, fix_stdout, fix_stderr = _run_command(fix_command, timeout)
    except StepTimeoutError:
        result["status"] = "fix_attempted"
        result["fix_stdout"] = f"Fix command timed out after {timeout}s"
        result["finished_at"] = _now_iso()
        return result

    result["fix_stdout"] = fix_stdout + "\n" + fix_stderr

    try:
        retry_code, retry_stdout, retry_stderr = _run_command(command, timeout)
    except StepTimeoutError:
        result["status"] = "fix_attempted"
        result["finished_at"] = _now_iso()
        return result

    result["exit_code"] = retry_code
    result["stdout"] = retry_stdout
    result["stderr"] = retry_stderr

    retry_combined = retry_stdout + "\n" + retry_stderr
    if _check_success(retry_code, retry_combined, action):
        result["status"] = "fixed"
    else:
        result["status"] = "fix_attempted"

    result["finished_at"] = _now_iso()
    return result
