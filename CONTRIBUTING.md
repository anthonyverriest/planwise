# Contributing to Planwise

Thanks for your interest in contributing. This document covers how to get set up, the conventions we follow, and how to propose changes.

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold it. Report unacceptable behavior to the maintainers.

## Ways to contribute

- **Report bugs** using the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
- **Propose features** using the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).
- **Ask questions** in [GitHub Discussions](https://github.com/anthonyverriest/planwise/discussions).
- **Submit pull requests** for fixes, features, or documentation.

Before starting non-trivial work, please open an issue to discuss the approach — this saves wasted effort if the change would conflict with planned direction.

## Development setup

Planwise uses [**uv**](https://github.com/astral-sh/uv) for environment and dependency management.

```bash
git clone https://github.com/anthonyverriest/planwise.git
cd planwise
uv sync
source .venv/bin/activate
```

Verify the CLI works:

```bash
pw --version
```

## Running tests

```bash
uv run pytest
```

Please include tests for new functionality and regressions. For bug fixes, demonstrate the test fails without the fix and passes with it.

## Code style

- Python 3 with PEP 585 typing.
- Follow PEP 8 and the conventions in [`CLAUDE.md`](CLAUDE.md) — it is the canonical style guide for this repo.
- Use Pydantic v2 for structured data.
- Keep functions small, pure, and single-purpose. Prefer composition over inheritance.
- Write self-explanatory code; avoid inline comments except for inherently complex logic.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add parallel agent dispatcher
fix: handle empty phase chain in /next
docs: clarify jj colocation in README
ref: extract workflow epilogue
```

Keep each commit focused. Prefer a series of small, reviewable commits over one large commit.

## Pull requests

1. Fork the repo and create your branch from `main` (or `dev` if actively used).
2. Make your changes following the style guide.
3. Add or update tests.
4. Ensure `uv run pytest` passes.
5. Update documentation (README, docstrings) where relevant.
6. Open a PR using the [PR template](.github/PULL_REQUEST_TEMPLATE.md) and link the issue it closes.

A maintainer will review. Expect iteration — review feedback is a normal part of the process.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).
