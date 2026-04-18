# Planwise

Structured planning for Claude Code. Project-local, jj-native (colocated with git).

## What it does

Planwise gives Claude Code a **planning layer**: features, tasks, dependencies, and status tracking — stored as markdown files inside your project.

> **Roadmap:** The CLI (`pw`) is designed to be agent-agnostic — support for other AI coding tools is planned for future releases.

```
plan  →  implement  →  test  →  optimize  →  memo

bug (captured anytime, independent flow)
```

## Install

Planwise ships a CLI (`pw` / `planwise`), so an isolated tool install is recommended.

### Prerequisites

Planwise workflows drive [**jj (Jujutsu)**](https://github.com/jj-vcs/jj) as the version control system. jj operates in **colocated mode** with an existing git repo — your git remote, CI, and teammates keep using git unchanged.

```bash
# Install jj — see https://github.com/jj-vcs/jj for your platform
cargo install --locked --bin jj jj-cli   # or: brew install jj, etc.

# In an existing git project, enable colocated jj:
cd your-project
jj git init --colocate
```

After colocation, every `jj commit` / `jj rebase` / `jj git push` roundtrips to git — `git log` on the remote shows conventional commits.

### Planwise CLI

**With uv (recommended):**

```bash
uv tool install git+https://github.com/anthonyverriest/planwise
```

**With pip / pipx:**

```bash
pipx install git+https://github.com/anthonyverriest/planwise
# or, into the current environment:
pip install git+https://github.com/anthonyverriest/planwise
```

Upgrade later with `uv tool upgrade planwise` or `pipx upgrade planwise`.

## Quick start

In your terminal:

```bash
cd your-project
pw init --project "myapp" --prefix "MA" --agent claude --rules python --layout python-web
```

This creates a `planwise/` directory, injects planwise instructions into `CLAUDE.md`, configures the Python ruleset, and seeds a project-specific package-layout section. Claude Code reads those instructions automatically, so it knows how to use `pw` commands when you ask it to plan, implement, or test a feature.

```bash
# Or without agent integration — just the planning directory
pw init --project "myapp" --prefix "MA" --rules python
```

Then, inside Claude Code, just ask:

```
"brief: add a filter to the member list"   # plan a small feature → creates a task issue
"task add-member-list-filter"              # execute the task — implement, test, optimize, memo
"plan user auth with JWT"                  # larger feature — creates sub-features
"plan user-auth"                           # plan from a backlog issue slug
"implement user-auth"                      # build the feature's sub-features
"test user-auth"                           # adversarial testing
```

**Small features** use `brief` → `task`. `brief` plans and creates a task issue, `task` implements, tests, optimizes, and updates the knowledge base in one go. No feature ceremony.

**Larger features** use `plan` → `implement` → `test` → `optimize` → `memo` as separate steps, with features, sub-features, subagents, and dependency graphs.

Both accept free text or an existing issue slug. When given a slug, the workflow reads the issue as starting context — so you can toss rough ideas into the backlog and flesh them out later.

### Advancing between phases — `/next`

Each workflow is already a standalone skill (`/plan`, `/brief`, `/implement`, etc.). To chain them without typing the next phase manually, use `/next`. It reads the pipeline state, figures out what comes next, and prints the expanded workflow into your conversation:

```
> /plan add oauth
> (iterate on the plan, feature issue gets created)
> /clear                       ← drops prior context; built-in Claude Code command
> /next                        ← loads /implement <slug> into the fresh window
> (iterate on implementation)
> /clear
> /next                        ← loads /test <slug>
> ...
```

Chains: `brief → task` for small features, `plan → implement → test → optimize → memo` for larger ones. `/next` on the last phase of either chain reports completion and clears the pipeline state. The slug of the feature/task issue created during `/plan` or `/brief` is auto-detected and threaded through.

If you ran several `/plan` or `/brief` (or a mix) before typing `/next`, the pipeline session tracks every issue created. `/next` alone will list the candidates:

```
Multiple issues created during this planning session:
  [feature] auth-oauth
  [feature] auth-saml
  [task]    fix-header

Re-run as: /next <slug>  to pick one.
```

`/next auth-oauth` picks that feature and routes to `/implement`; `/next fix-header` picks the task and routes to `/task`.

The `/clear` is what gives each phase a fresh context window; pipeline state lives on disk (`planwise/.pipeline-state.json`), so `/clear` doesn't break the chain.

## How it works

```
You (in Claude Code)          Claude Code                    pw CLI
─────────────────────         ──────────────────             ──────────────────
"plan user auth"         →    pw run plan user auth     →    outputs workflow template
                              reads template, follows it
                              asks you questions (plan)
                              pw create feature "..."         creates issue files
                              pw dep add ...                 wires dependencies
                              ...
```

- **You talk to Claude Code.** You describe what you want in natural language.
- **Claude Code runs `pw` commands.** It loads the workflow template, then uses `pw` subcommands (`create`, `status`, `dep add`, `ready`, etc.) to manage issues as the workflow directs.
- **You don't run workflows directly.** The `pw run <workflow>` command outputs a markdown template — it's meant to be consumed by Claude Code, not read by you in a terminal.

### What you run (your terminal)

| Command | When |
|---------|------|
| `uv tool install git+https://github.com/anthonyverriest/planwise` | Once, to install |
| `pw init --project "name" --prefix "XX" --agent claude --layout python-web` | Once per project, to set up |
| `pw verify [--fix]` | Anytime, to check data integrity |
| `pw stats` | Anytime, to see project status |

### What Claude Code runs (during workflows)

| Command | Purpose |
|---------|---------|
| `pw run <workflow> [args]` | Load a workflow template |
| `pw create <type> "title"` | Create issues |
| `pw view / edit / status / close` | Manage issues |
| `pw dep add / remove / list` | Wire dependencies |
| `pw ready / blocked / next` | Query the dependency graph |
| `pw note <slug> "text"` | Add notes to issues |
| `pw sync exec / state / reset` | Execute sync pipeline steps |

You _can_ run any `pw` command yourself — they're just CLI commands. But during workflows, Claude Code drives them.

## Workflows

Planwise ships 7 workflow templates:

| Workflow | Purpose |
|----------|---------|
| `brief` | Lightweight planning for a small feature or fix — produces a task issue |
| `task` | Execute a task — implement, test, optimize, and memo in one pass |
| `plan` | Design a feature, stress-test it, create sub-features |
| `implement` | Build a feature's sub-features via dependency graph and subagents |
| `test` | Adversarial testing across 6 attack dimensions |
| `optimize` | Codebase evolution engine across 4 dimensions |
| `bug` | Capture bugs during UAT |
| `memo` | Distill a completed feature into the knowledge base |
| `sync` | Walk multi-step operations (e.g., dev→prod) with the agent — catches missed steps, diagnoses failures across tools |

### Sync pipelines

Define multi-step operations (migrations, deployments, environment syncs) as a simple YAML checklist. Claude Code walks each step with you — executing commands, gating destructive steps for human approval, and diagnosing failures using cross-step context and codebase knowledge.

In your terminal:

```bash
pw sync init              # scaffold a starter sync.yml
```

Edit `planwise/sync.yml` to define your steps:

```yaml
name: dev-to-prod
steps:
  - name: migrate-db
    plugin: alembic
    action: upgrade head
    gate: human
  - name: apply-infra
    plugin: terraform
    action: apply
    gate: human
  - name: verify-health
    plugin: shell
    action: curl -f https://api.example.com/health
```

Then, in Claude Code:

```
"run the sync pipeline"
```

The agent checks preconditions between steps (e.g., won't run `terraform apply` if the migration was skipped), pattern-matches known failures, and proposes fixes by reading your codebase — not just the error output.

## Rulesets

Rulesets inject language-specific and domain-specific rules into coding workflows (`task`, `implement`, `test`, `optimize`). Planning workflows (`brief`, `plan`, `memo`, `bug`) don't receive rules — they don't write code.

Set project defaults at init:

```bash
pw init --project "myapp" --prefix "MA" --rules python
pw init --rules design              # add a ruleset to an existing project
```

Override per run:

```bash
pw run implement user-auth --rules python,design
```

Override replaces the project defaults for that invocation. A `base` ruleset with universal coding rules always injects automatically when any ruleset is active.

Planwise ships with built-in rulesets. The `$RULES` marker in workflow templates is replaced with the combined ruleset content at runtime.

| Ruleset | Scope |
|---------|-------|
| `base` | Universal coding rules (always injected when any ruleset is active) |
| `python` | Python-specific rules |
| `ts-web` | TypeScript/JavaScript web rules (React) |
| `rust-web` | Rust web rules (Tokio, Axum) |
| `design` | Software architecture and design principles (SOLID, DDD, Hexagonal) |
| `finance` | Financial engineering (idempotency, precision, distributed consistency) |
| `ui-ux` | UI/UX design guidelines (layout, typography, color, forms) |

## Layouts

Layouts are project-shape scaffolds — the package/directory structure for a given project type — appended directly to `CLAUDE.md` as a `<layout>...</layout>` section. Unlike rulesets (which carry coding behavior and are runtime-injected into workflow templates), layouts only describe *where code lives*. Once seeded, the section is yours to edit: re-running `pw init --layout X` skips when a `<layout>` block is already present, so your changes are never overwritten.

Layouts complement rulesets. Rulesets cover coding behavior (idioms, forbidden libs, framework conventions) scoped to coding workflows. Layouts give the agent always-on structural orientation (which directory holds the domain logic, where adapters live, etc.) without polluting planning workflows or general chat with code rules.

Seeding is a single write: the layout content is appended to `CLAUDE.md` inside a `<layout>...</layout>` block. If `CLAUDE.md` is missing or lacks the planwise coding-standards block, it's seeded too — so `--layout` alone produces a complete, standalone `CLAUDE.md`.

Set at init (or add later):

```bash
pw init --project "myapp" --prefix "MA" --agent claude --layout python-web
pw init --layout python-web              # seed a layout into an existing project
```

| Layout | Scope |
|--------|-------|
| `python-web` | Python web API (hexagonal: `domain/`, `adapters/`, `api/`, `core/`) |

## Storage

- Each project gets a `planwise/` directory with markdown files organized by status
- Issues use YAML frontmatter for metadata, markdown body for details
- Dependencies form a DAG — `ready` shows what's unblocked, `blocked` shows what's waiting
- File-based storage means everything is version-controllable and diffable

## Parallel execution

Parallelism operates at two levels, both using **jj workspaces** (jj's equivalent of git worktrees, backed by a single shared repo and the operation log):

- **Multiple features concurrently.** Launch separate Claude Code sessions, each implementing a different feature in its own jj workspace on its own feature bookmark. The per-feature lock check ensures no two sessions work on the same feature, while the shared `planwise/` directory keeps issue state consistent across workspaces. Stale working copies (caused by another workspace rewriting a shared change) are reconciled with `jj workspace update-stale`.
- **Multiple sub-features within a feature.** When the dependency graph surfaces independent sub-features (no mutual deps), the `implement` workflow dispatches them concurrently — one subagent per sub-feature, each in an isolated jj workspace. After all complete, all sub-feature heads merge into the feature change in a **single n-way merge**. Conflicts are recorded inline as first-class data in the change graph (not a fatal error) and are resolved in-place by Claude during the same `/implement` phase — no work is discarded, no sequential re-implementation fallback.

No manual workspace setup needed. The workflow detects whether it's running in a non-default workspace and adjusts its behavior (skips bookmark creation, relaxes the multi-feature lock check).

## CLI reference

`pw` (or `planwise`) is the CLI. All commands output JSON by default, text with `-t`.

| Command | Description |
|---------|-------------|
| `init --project "name" --prefix "XX" [--agent claude] [--rules python] [--layout python-web]` | Initialize planning (re-run with `--agent`/`--rules`/`--layout` to update) |
| `create <feature\|sub-feature\|task\|uat\|bug> "title"` | Create an issue (body from stdin) |
| `view <slug>` | View an issue |
| `edit <slug> --title/--body/--label/--agent` | Edit an issue |
| `status <slug> <status>` | Move issue to backlog/ready/in-progress/in-review/done |
| `close <slug> --reason "..."` | Close an issue |
| `list [type] [--status S] [--children-of slug]` | List issues with filters |
| `dep add/remove/list <slug> [dep-slug]` | Manage dependencies (with cycle detection) |
| `ready [--children-of slug]` | Issues with all dependencies satisfied |
| `blocked [--children-of slug]` | Issues with unsatisfied dependencies |
| `next` | Pick the next issue to work on |
| `search "query"` | Search issues |
| `note <slug> "text"` | Add a timestamped note |
| `stats` | Counts by status and type |
| `verify [--fix]` | Check integrity, optionally auto-fix |
| `run <workflow> [args...] [--list] [--rules name]` | Output a workflow template (rulesets and `$ARGUMENTS` replaced) |
| `sync init [--pipeline path]` | Scaffold a starter `sync.yml` pipeline config |
| `sync show [--pipeline path]` | Display pipeline steps, gates, and current state |
| `sync exec <step> [--pipeline path] [--force]` | Execute a single pipeline step |
| `sync state [step]` | Show pipeline execution state |
| `sync reset [step] [--all]` | Reset step state (one step or all) |

## License

MIT
