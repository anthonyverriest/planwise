# Changelog

## Unreleased

- feat: `--layout` flag on `pw init` seeds a project's package-layout scaffolding (directory structure) by appending a `<layout>...</layout>` section directly to `CLAUDE.md` — no separate file, no `@` import. First layout: `python-web` (hexagonal: `domain/`, `adapters/`, `api/`, `core/`). Re-runs skip when a `<layout>` block is already present in `CLAUDE.md`, preserving user edits. Coding behavior (libs, conventions, forbidden) stays in rulesets.
- fix: `pw init --layout X` without `--agent claude` now also seeds the planwise coding-standards block into `CLAUDE.md`, so `--layout` alone produces a complete, standalone `CLAUDE.md` instead of a one-liner.
