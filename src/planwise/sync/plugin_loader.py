"""Plugin discovery and YAML loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from planwise.sync.errors import PluginValidationError
from planwise.sync.types import FailurePattern, Plugin, PluginAction


_BUILTIN_PLUGINS_DIR = Path(__file__).parent / "plugins"

_REQUIRED_PLUGIN_FIELDS = {"name", "description", "actions"}
_REQUIRED_ACTION_FIELDS = {"command"}
_REQUIRED_FAILURE_FIELDS = {"pattern", "message", "fix"}


def _validate_failure_pattern(raw: dict, plugin_name: str, action_name: str) -> FailurePattern:
    """Validate and convert a raw failure pattern dict."""
    missing = _REQUIRED_FAILURE_FIELDS - raw.keys()
    if missing:
        raise PluginValidationError(
            f"Plugin '{plugin_name}' action '{action_name}' failure pattern "
            f"missing fields: {', '.join(sorted(missing))}"
        )
    return FailurePattern(
        pattern=str(raw["pattern"]),
        message=str(raw["message"]),
        fix=str(raw["fix"]),
    )


def _validate_action(raw: dict, plugin_name: str, action_name: str) -> PluginAction:
    """Validate and convert a raw action dict."""
    missing = _REQUIRED_ACTION_FIELDS - raw.keys()
    if missing:
        raise PluginValidationError(
            f"Plugin '{plugin_name}' action '{action_name}' "
            f"missing fields: {', '.join(sorted(missing))}"
        )
    action = PluginAction(command=str(raw["command"]))
    if "success_pattern" in raw:
        action["success_pattern"] = str(raw["success_pattern"])
    if "failure_patterns" in raw:
        action["failure_patterns"] = [
            _validate_failure_pattern(fp, plugin_name, action_name)
            for fp in raw["failure_patterns"]
        ]
    if "context" in raw:
        action["context"] = str(raw["context"])
    if "timeout" in raw:
        action["timeout"] = int(raw["timeout"])
    return action


def _load_plugin_file(path: Path) -> Plugin:
    """Load and validate a single plugin YAML file."""
    text = path.read_text(encoding="utf-8")
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise PluginValidationError(f"Plugin file is not a YAML mapping: {path}")

    missing = _REQUIRED_PLUGIN_FIELDS - raw.keys()
    if missing:
        raise PluginValidationError(
            f"Plugin file {path} missing fields: {', '.join(sorted(missing))}"
        )

    plugin_name = str(raw["name"])
    raw_actions = raw["actions"]
    if not isinstance(raw_actions, dict):
        raise PluginValidationError(
            f"Plugin '{plugin_name}' actions must be a mapping, got {type(raw_actions).__name__}"
        )

    actions: dict[str, PluginAction] = {}
    for action_name, action_raw in raw_actions.items():
        actions[str(action_name)] = _validate_action(action_raw, plugin_name, str(action_name))

    return Plugin(
        name=plugin_name,
        description=str(raw["description"]),
        actions=actions,
    )


def _load_plugins_from_dir(directory: Path) -> dict[str, Plugin]:
    """Load all .yml plugins from a directory."""
    plugins: dict[str, Plugin] = {}
    if not directory.is_dir():
        return plugins
    for path in sorted(directory.glob("*.yml")):
        plugin = _load_plugin_file(path)
        plugins[plugin["name"]] = plugin
    return plugins


def discover_plugins(plugin_dirs: list[str], pipeline_dir: Path) -> dict[str, Plugin]:
    """Load all plugins: built-in first, then user-defined (user overrides built-in by name).

    Args:
        plugin_dirs: Additional directories from pipeline config, resolved relative to pipeline_dir.
        pipeline_dir: Parent directory of the pipeline YAML file.
    """
    plugins = _load_plugins_from_dir(_BUILTIN_PLUGINS_DIR)

    for rel_dir in plugin_dirs:
        user_dir = (pipeline_dir / rel_dir).resolve()
        user_plugins = _load_plugins_from_dir(user_dir)
        plugins.update(user_plugins)

    return plugins
