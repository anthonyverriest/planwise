# Changelog

## Unreleased

- feat: `--layout` flag on `pw init` seeds a project's package-layout scaffolding (directory structure). The layout content is written to `planwise/layout.md` and referenced from `CLAUDE.md` via a single `@planwise/layout.md` import — no inline markers. First layout: `python-web` (hexagonal: `domain/`, `adapters/`, `api/`, `core/`). Re-runs skip when `planwise/layout.md` already exists; the `@` import line is self-healing. Coding behavior (libs, conventions, forbidden) stays in rulesets.
