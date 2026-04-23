"""Agent Protocol and shared types."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from planwise.agents.capabilities import Capability


@dataclass(frozen=True)
class InstallReport:
    """Result of an Agent.install() call.

    Attributes:
        instruction_file: Path to the written/updated instruction file.
        instruction_skipped: True when coding standards were already present.
        layout_skipped: True when the layout block was already present.
        skills_created: Paths of skill/subagent files emitted by install.
    """

    instruction_file: Path
    instruction_skipped: bool = False
    layout_skipped: bool = False
    skills_created: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class RenderContext:
    """Context threaded through directive rendering."""

    workflow_name: str


@runtime_checkable
class Agent(Protocol):
    """Target agent interface.

    `install` is the only side-effectful method. Rendering methods are pure
    so workflows can be golden-tested offline.
    """

    name: ClassVar[str]
    instruction_file: ClassVar[str]
    capabilities: ClassVar[frozenset[Capability]]

    def install(self, project_dir: Path, *, layout: str | None = None) -> InstallReport: ...

    def uninstall(self, project_dir: Path) -> int: ...

    def render_workflow(self, workflow_name: str, body: str) -> str: ...
