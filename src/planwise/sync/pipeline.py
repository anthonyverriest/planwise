"""Pipeline YAML loading and validation."""

from __future__ import annotations

from pathlib import Path

import yaml

from planwise.sync.errors import ActionNotFoundError, PipelineValidationError, PluginNotFoundError
from planwise.sync.types import GateType, PipelineConfig, PipelineStep, Plugin


_VALID_GATES: set[GateType] = {"auto", "human"}
_REQUIRED_PIPELINE_FIELDS = {"name", "steps"}
_REQUIRED_STEP_FIELDS = {"name"}


def _validate_step(raw: dict, index: int) -> PipelineStep:
    """Validate and convert a raw step dict."""
    missing = _REQUIRED_STEP_FIELDS - raw.keys()
    if missing:
        raise PipelineValidationError(
            f"Step {index} missing fields: {', '.join(sorted(missing))}"
        )

    has_plugin = "plugin" in raw and "action" in raw
    has_inline = "run" in raw
    if not has_plugin and not has_inline:
        raise PipelineValidationError(
            f"Step '{raw['name']}' must have either 'plugin'+'action' or 'run'"
        )
    if has_plugin and has_inline:
        raise PipelineValidationError(
            f"Step '{raw['name']}' cannot have both 'plugin'+'action' and 'run'"
        )

    gate = raw.get("gate", "auto")
    if gate not in _VALID_GATES:
        raise PipelineValidationError(
            f"Step '{raw['name']}' has invalid gate '{gate}', must be one of: {', '.join(_VALID_GATES)}"
        )

    step = PipelineStep(name=str(raw["name"]))
    if has_plugin:
        step["plugin"] = str(raw["plugin"])
        step["action"] = str(raw["action"])
    if has_inline:
        step["run"] = str(raw["run"])
    step["gate"] = gate
    if "params" in raw:
        step["params"] = {str(k): str(v) for k, v in raw["params"].items()}
    return step


def load_pipeline(path: Path) -> PipelineConfig:
    """Load and structurally validate a pipeline YAML file."""
    if not path.is_file():
        raise PipelineValidationError(f"Pipeline file not found: {path}")

    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise PipelineValidationError(f"Pipeline file is not a YAML mapping: {path}")

    missing = _REQUIRED_PIPELINE_FIELDS - raw.keys()
    if missing:
        raise PipelineValidationError(
            f"Pipeline file {path} missing fields: {', '.join(sorted(missing))}"
        )

    raw_steps = raw["steps"]
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PipelineValidationError("Pipeline must have at least one step")

    steps: list[PipelineStep] = []
    seen_names: set[str] = set()
    for i, raw_step in enumerate(raw_steps):
        step = _validate_step(raw_step, i)
        if step["name"] in seen_names:
            raise PipelineValidationError(f"Duplicate step name: '{step['name']}'")
        seen_names.add(step["name"])
        steps.append(step)

    return PipelineConfig(
        name=str(raw["name"]),
        description=str(raw.get("description", "")),
        steps=steps,
        plugin_dirs=[str(d) for d in raw.get("plugin_dirs", [])],
    )


def validate_pipeline_plugins(config: PipelineConfig, plugins: dict[str, Plugin]) -> None:
    """Verify all plugin/action references in the pipeline resolve to loaded plugins."""
    for step in config["steps"]:
        plugin_name = step.get("plugin")
        if plugin_name is None:
            continue

        if plugin_name not in plugins:
            raise PluginNotFoundError(
                f"Step '{step['name']}' references plugin '{plugin_name}' "
                f"which was not found. Available: {', '.join(sorted(plugins))}"
            )

        action_name = step.get("action", "")
        plugin = plugins[plugin_name]
        if action_name not in plugin["actions"]:
            raise ActionNotFoundError(
                f"Step '{step['name']}' references action '{action_name}' "
                f"in plugin '{plugin_name}' which does not exist. "
                f"Available: {', '.join(sorted(plugin['actions']))}"
            )
