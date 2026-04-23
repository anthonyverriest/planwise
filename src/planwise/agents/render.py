"""Directive IR — Jinja2-driven workflow rendering.

Workflows are markdown templates rendered through a deliberately narrow Jinja2
environment. Four helpers are exposed; each builds a typed directive, hands it
to the active agent, and returns the agent's rendered string:

    {{ ask(prompt="…", choices=[…], section="…", multi_select=false) }}
    {{ dispatch(agent="Explore", mode="quick", protocol="…#…",
                inputs={"k": "v"}, readonly=true, body="…") }}
    {{ invoke(phase="next", args="$ARGUMENTS") }}
    {{ skill_ref(name="plan") }}

No other Python is exposed — no loops, no conditionals, no arbitrary attribute
access. The environment also exposes a `caps` mapping so templates can do
capability checks sparingly via `{% if caps.STRUCTURED_QUESTIONS %}`.

Malformed kwargs surface as `DirectiveError` at render time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from jinja2 import Environment, StrictUndefined
from jinja2 import TemplateSyntaxError

from planwise.agents.base import RenderContext
from planwise.agents.capabilities import Capability


class DirectiveError(ValueError):
    """Raised when a directive call has invalid kwargs."""


@dataclass(frozen=True)
class AskDirective:
    prompt: str
    section: str | None = None
    choices: list[Any] | None = None
    multi_select: bool = False


@dataclass(frozen=True)
class DispatchDirective:
    """Heading-only dispatch marker; the protocol body stays as prose blockquote.

    `task` is the human label ("KB retriever"). `detail` is the parenthesized
    qualifier ("Explore, quick" / "general-purpose, fresh context"). Optional
    `agent` + `mode` are for non-Claude renderers that need structured info.
    """

    task: str
    detail: str | None = None
    level: int = 3
    agent: str | None = None
    mode: str | None = None
    prefix: str = ""


@dataclass(frozen=True)
class InvokeDirective:
    phase: str
    args: str = ""


@dataclass(frozen=True)
class SkillRefDirective:
    name: str


class DirectiveRenderer(Protocol):
    """Per-agent renderer contract."""

    capabilities: frozenset[Capability]

    def render_ask(self, d: AskDirective, ctx: RenderContext) -> str: ...
    def render_dispatch(self, d: DispatchDirective, ctx: RenderContext) -> str: ...
    def render_invoke(self, d: InvokeDirective, ctx: RenderContext) -> str: ...
    def render_skill_ref(self, d: SkillRefDirective, ctx: RenderContext) -> str: ...
    def render_arguments(self, ctx: RenderContext) -> str: ...


def _build_helpers(
    renderer: DirectiveRenderer, ctx: RenderContext
) -> dict[str, Callable[..., str]]:
    """Wrap each typed directive + renderer call as a Jinja2-callable helper."""

    def ask(
        prompt: str,
        section: str | None = None,
        choices: list[Any] | None = None,
        multi_select: bool = False,
    ) -> str:
        try:
            directive = AskDirective(
                prompt=prompt,
                section=section,
                choices=choices,
                multi_select=bool(multi_select),
            )
        except TypeError as exc:
            raise DirectiveError(f"ask(): {exc}") from exc
        return renderer.render_ask(directive, ctx)

    def dispatch(
        task: str,
        detail: str | None = None,
        level: int = 3,
        agent: str | None = None,
        mode: str | None = None,
        prefix: str = "",
    ) -> str:
        try:
            directive = DispatchDirective(
                task=task,
                detail=detail,
                level=int(level),
                agent=agent,
                mode=mode,
                prefix=str(prefix),
            )
        except TypeError as exc:
            raise DirectiveError(f"dispatch(): {exc}") from exc
        return renderer.render_dispatch(directive, ctx)

    def invoke(phase: str, args: str = "") -> str:
        try:
            directive = InvokeDirective(phase=phase, args=str(args))
        except TypeError as exc:
            raise DirectiveError(f"invoke(): {exc}") from exc
        return renderer.render_invoke(directive, ctx)

    def skill_ref(name: str) -> str:
        try:
            directive = SkillRefDirective(name=name)
        except TypeError as exc:
            raise DirectiveError(f"skill_ref(): {exc}") from exc
        return renderer.render_skill_ref(directive, ctx)

    def arguments() -> str:
        return renderer.render_arguments(ctx)

    return {
        "ask": ask,
        "dispatch": dispatch,
        "invoke": invoke,
        "skill_ref": skill_ref,
        "arguments": arguments,
    }


def _make_env() -> Environment:
    """Jinja2 environment tuned for markdown: no auto-escape, preserve whitespace."""
    return Environment(
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
        undefined=StrictUndefined,
    )


_ENV = _make_env()


def render(text: str, renderer: DirectiveRenderer, ctx: RenderContext) -> str:
    """Render a workflow markdown template using `renderer` as the directive backend."""
    helpers = _build_helpers(renderer, ctx)
    caps = {c.name: (c in renderer.capabilities) for c in Capability}
    try:
        template = _ENV.from_string(text)
    except TemplateSyntaxError as exc:
        raise DirectiveError(f"template syntax error in {ctx.workflow_name!r}: {exc.message}") from exc
    return template.render(caps=caps, **helpers)


class NullRenderer:
    """Stringifies every directive to a compact marker — for tests/debugging."""

    capabilities: frozenset[Capability] = frozenset()

    def render_ask(self, d: AskDirective, ctx: RenderContext) -> str:
        return f"[[ask {d.section or d.prompt[:24]}]]"

    def render_dispatch(self, d: DispatchDirective, ctx: RenderContext) -> str:
        return f"[[dispatch {d.agent}]]"

    def render_invoke(self, d: InvokeDirective, ctx: RenderContext) -> str:
        return f"[[invoke {d.phase}]]"

    def render_skill_ref(self, d: SkillRefDirective, ctx: RenderContext) -> str:
        return f"[[skill {d.name}]]"

    def render_arguments(self, ctx: RenderContext) -> str:
        return "[[arguments]]"
