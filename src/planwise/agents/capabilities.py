"""Agent capability flags — declare what each target agent supports."""

from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    """Capabilities a target agent may support.

    Used to drive directive rendering without per-agent branches in workflows.
    """

    EXECUTABLE_COMMANDS = "executable_commands"
    STRUCTURED_QUESTIONS = "structured_questions"
    NAMED_SUBAGENTS = "named_subagents"
    BUILTIN_EXPLORE = "builtin_explore"
    SLASH_INVOKE = "slash_invoke"
    SLASH_CHAINING = "slash_chaining"
    SETTINGS_FILE = "settings_file"
