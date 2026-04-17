"""Sync-specific exception hierarchy."""

from __future__ import annotations


class SyncError(Exception):
    """Base exception for all sync errors."""


class PluginNotFoundError(SyncError):
    """Referenced plugin does not exist in any search path."""


class PluginValidationError(SyncError):
    """Plugin YAML file has invalid structure or missing required fields."""


class ActionNotFoundError(SyncError):
    """Referenced action does not exist in the plugin."""


class PipelineValidationError(SyncError):
    """Pipeline YAML is structurally invalid or references missing resources."""


class StepTimeoutError(SyncError):
    """Step command exceeded its configured timeout."""


class StateCorruptedError(SyncError):
    """State JSON file is malformed or inconsistent with the pipeline."""
