# Planwise

**Spec-driven development for AI coding agents.** A planning layer, a dependency graph, and a parallel-agent runtime — so your AI coding agent ships features, not vibes.

> From *vibe coding* to *spec-driven coding*: Planwise turns rough ideas into structured specs, then drives your agent through plan → implement → test → optimize with per-phase context windows and multi-agent orchestration.

**Supported agents:** Claude Code (reference) and Cursor. One canonical workflow markdown; each agent renders its own native primitives (skills vs. subagents, `AskUserQuestion` vs. `AskQuestion`, etc.).

```
plan  →  implement  →  test  →  optimize  →  memo
                  ↑
           (bug: captured anytime)
```

Agentic workflows. Context engineering built in. File-based, git-native, zero lock-in.

---

## Why Planwise

Autonomous coding agents are compressing delivery timelines from weeks to days — **if** you feed them the right context. Raw chat prompts don't scale past small features. Planwise is the missing planning layer:

- **Spec-driven, not vibe-driven.** Every feature gets a structured issue with goals, dependencies, and acceptance criteria *before* a line of code is written.
- **Context engineering by default.** Each workflow phase runs in its own context window — no more 200k-token soup where the agent forgets what it's building.
- **Parallel agents, real graph.** Independent sub-features dispatch concurrently to subagents in isolated workspaces, then merge back in a single n-way merge.
- **Agent-driven, human-steered.** You talk to your agent. The agent runs `pw` commands. You review the diff.
- **Git-native storage.** Issues are markdown files. The knowledge base is markdown. Everything diffs, everything versions.
- **Agent-agnostic by design.** Workflows are authored once in a directive IR and rendered per-agent; Claude Code is the reference, Cursor ships, Codex is on the roadmap.

---

## Install

Planwise ships a CLI (`pw` / `planwise`). Isolate it.

### Prerequisites

Workflows drive [**jj (Jujutsu)**](https://github.com/jj-vcs/jj) in **colocated mode** alongside git — your remote, CI, and teammates keep using git unchanged.

```bash
cargo install --locked --bin jj jj-cli        # or: brew install jj
```

`pw init` handles the colocation for you: if the project directory has no `.jj/`, it runs `jj git init --colocate` (creating `.git/` too if needed, or adding jj alongside an existing git repo). Pass `--no-vcs` to skip.

Every `jj commit` / `jj rebase` / `jj git push` roundtrips to git. Conventional commits land on the remote.

### Planwise CLI

```bash
# With uv (recommended)
uv tool install git+https://github.com/anthonyverriest/planwise

# With pipx
pipx install git+https://github.com/anthonyverriest/planwise
```

Upgrade with `uv tool upgrade planwise` or `pipx upgrade planwise`.

---

## Quick start

```bash
cd your-project
pw init --project "myapp" --prefix "MA" --agent claude --rules python --layout python-web
# or for Cursor:
pw init --project "myapp" --prefix "MA" --agent cursor --rules python --layout python-web
```

Claude install lays down `CLAUDE.md` + `.claude/skills/<workflow>/SKILL.md` + `.claude/settings.json` (adds `pw`/`planwise`/`grep`/`ls` to the allow-list). Cursor install lays down `.cursor/rules/planwise.mdc` + `.cursor/agents/<workflow>.md` subagents (thin shell shims that fetch the workflow body at runtime via `pw -t run --agent cursor`). Both agents pick their install up automatically.

Then, inside your agent:

```
"brief: add a filter to the member list"    # small feature → one task issue
"task add-member-list-filter"               # implement + test + optimize + memo in one pass
"plan user auth with JWT"                   # larger feature → sub-features + dep graph
"implement user-auth"                       # parallel subagents build sub-features
"test user-auth"                            # adversarial testing across 6 attack dimensions
```

**Small features:** `brief → task`. Plan, then execute in one shot. No ceremony.

**Larger features:** `plan → implement → test → optimize → memo`. Separate phases, separate context windows, parallel sub-feature execution, a knowledge-base distillation at the end.

Both accept free text *or* an existing issue slug — toss rough ideas into the backlog, flesh them out later.

### Phase chaining — `/next`

Each workflow is a standalone slash command — a skill in Claude Code, a subagent in Cursor. `/next` reads pipeline state and loads the next phase into a fresh window:

```
> /plan add oauth
> (iterate — feature issue gets created)
> /clear                       ← fresh context (built-in Claude Code command)
> /next                        ← auto-loads /implement <slug>
> /clear
> /next                        ← auto-loads /test <slug>
> ...
```

Pipeline state lives on disk (`planwise/.pipeline-state.json`), so `/clear` never breaks the chain. If multiple plans ran before `/next`, it lists candidates:

```
Multiple issues created during this planning session:
  [feature] auth-oauth
  [feature] auth-saml
  [task]    fix-header

Re-run as: /next <slug>  to pick one.
```

---

## How it works

```
You (in your agent)          Your agent                     pw CLI
─────────────────────        ──────────────────             ──────────────────
"plan user auth"         →   pw run plan user auth     →    outputs workflow template
                             reads template, follows it
                             asks clarifying questions
                             pw create feature "..."         creates issue files
                             pw dep add ...                  wires dependencies
                             ...
```

- **You describe intent in natural language.** The agent does the plumbing.
- **Your agent runs `pw` commands.** It loads the workflow template, then drives `pw` subcommands (`create`, `status`, `dep add`, `ready`, etc.) as the workflow directs.
- **You don't run workflows directly.** `pw run <workflow>` outputs a markdown template — consumed by the agent, not read in a terminal.
- **One source of truth, per-agent rendering.** Workflows are authored once; Claude renders them one way (`$ARGUMENTS`, `AskUserQuestion`, `!`backtick auto-exec`), Cursor renders them another (`<the user's task>`, `AskQuestion`, Bash subagent dispatch). Golden tests pin both.

### What *you* run (your terminal)

| Command | When |
|---------|------|
| `uv tool install git+https://github.com/anthonyverriest/planwise` | Once, to install |
| `pw init --project "name" --prefix "XX" --agent {claude\|cursor} --layout python-web` | Once per project |
| `pw claude` | Fresh jj workspace + launch Claude Code in it (for multi-feature concurrency) |
| `pw cursor` | Fresh jj workspace + open it in a new Cursor window (same, for Cursor users) |
| `pw verify [--fix]` | Anytime, to check data integrity |
| `pw stats` | Anytime, to see project status |

### What *your agent* runs (during workflows)

| Command | Purpose |
|---------|---------|
| `pw run <workflow> [args] [--agent claude\|cursor]` | Load a workflow template rendered for the active agent |
| `pw create <type> "title"` | Create issues |
| `pw view / edit / status / close` | Manage issues |
| `pw dep add / remove / list` | Wire dependencies |
| `pw ready / blocked / next` | Query the dependency graph |
| `pw note <slug> "text"` | Add notes to issues |
| `pw sync exec / state / reset` | Execute sync pipeline steps |

You *can* run any `pw` command yourself — they're just CLI. But during workflows, the agent drives.

### Agents

| Agent | Install target | Invocation | Runtime |
|-------|----------------|------------|---------|
| `claude` | `CLAUDE.md` + `.claude/skills/<name>/SKILL.md` + `.claude/settings.json` | `/<workflow>` (auto-exec via `!`backticks) | Native skills, `AskUserQuestion`, `Agent` tool, `Explore`/`general-purpose` subagents |
| `cursor` | `.cursor/rules/planwise.mdc` + `.cursor/agents/<name>.md` | `/<workflow>` (subagent dispatches Bash for `pw` calls) | Native subagents, `AskQuestion` (model-dependent) with chat fallback, built-in `Explore`, custom `planwise-worker` for general-purpose dispatches |

Cursor subagents are thin shell shims — they fetch the workflow body at runtime via `pw -t run --agent cursor <name>`, so upgrading Planwise updates workflow behavior without regenerating `.cursor/agents/`. Multiple agents can be installed side-by-side in the same repo.

---

## Workflows

Planwise ships 9 workflow templates:

| Workflow | Purpose |
|----------|---------|
| `brief` | Lightweight planning for a small feature/fix — produces a task issue |
| `task` | Execute a task — implement, test, optimize, memo in one pass |
| `plan` | Design a feature, stress-test it, create sub-features |
| `implement` | Build a feature's sub-features via dep graph + parallel subagents |
| `test` | Adversarial testing across 6 attack dimensions |
| `optimize` | Codebase evolution engine across 4 dimensions |
| `bug` | Capture bugs during UAT |
| `memo` | Distill a completed feature into the knowledge base |
| `sync` | Walk multi-step ops (dev→prod, migrations) — catches missed steps, diagnoses failures across tools |

### Sync pipelines

Define migrations, deployments, and environment syncs as a YAML checklist. Your agent walks each step with you — executing commands, gating destructive steps for human approval, and diagnosing failures using cross-step context and codebase knowledge.

```bash
pw sync init              # scaffold planwise/sync.yml
```

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

Then, in your agent:

```
"run the sync pipeline"
```

Your agent checks preconditions between steps (won't `terraform apply` if the migration was skipped), pattern-matches known failures, and proposes fixes by reading your codebase — not just the error output.

---

## Rulesets

Rulesets inject language- and domain-specific rules into coding workflows (`task`, `implement`, `test`, `optimize`). Planning workflows (`brief`, `plan`, `memo`, `bug`) don't receive rules — they don't write code.

```bash
pw init --project "myapp" --prefix "MA" --rules python       # default at init
pw init --rules design                                       # add to existing project
pw run implement user-auth --rules python,design             # override per run
```

A `base` ruleset with universal coding rules always injects when any ruleset is active. The `$RULES` marker in templates is replaced at runtime.

| Ruleset | Scope |
|---------|-------|
| `base` | Universal coding rules (always injected) |
| `python` | Python-specific rules |
| `ts-web` | TypeScript/JavaScript (React) |
| `rust-web` | Rust web (Tokio, Axum) |
| `design` | SOLID, DDD, Hexagonal |
| `finance` | Financial engineering (idempotency, precision, distributed consistency) |
| `ui-ux` | UI/UX design guidelines |

---

## Layouts

Layouts are project-shape scaffolds — the package/directory structure — appended to the agent's instruction file (`CLAUDE.md` or `.cursor/rules/planwise.mdc`) inside a `<layout>...</layout>` block. Unlike rulesets (runtime-injected coding behavior), layouts give the agent **always-on structural orientation**: which directory holds domain logic, where adapters live, etc.

Once seeded, the block is yours — re-running `pw init --layout X` skips when a `<layout>` block already exists.

```bash
pw init --project "myapp" --prefix "MA" --agent claude --layout python-web
pw init --layout python-web              # add to existing project
```

| Layout | Scope |
|--------|-------|
| `python-web` | Python web API (hexagonal: `domain/`, `adapters/`, `api/`, `core/`) |

---

## Parallel agents

Parallelism runs at two levels, both on **jj workspaces** (jj's worktree equivalent, backed by a shared repo + operation log):

- **Multiple features concurrently.** Spin up separate agent sessions, each in its own workspace on its own feature bookmark. `pw claude` / `pw cursor` handle the workspace creation + launch in one step — `jj git fetch`, `jj workspace add -r dev@origin`, then exec Claude (CLI replaces the shell) or spawn a detached Cursor window. A per-feature lock check prevents collisions; the shared `planwise/` directory keeps issue state consistent. Stale working copies reconcile via `jj workspace update-stale`.
- **Multiple sub-features within a feature.** When the dep graph surfaces independent sub-features, `implement` dispatches them concurrently — one subagent per sub-feature, each in an isolated workspace. All sub-feature heads then merge into the feature change in a **single n-way merge**. Conflicts are first-class data in the change graph (not fatal), resolved in-place during the same `/implement` phase. No work discarded, no sequential fallback.

No manual workspace setup. Workflows detect non-default workspaces and adjust (skip bookmark creation, relax multi-feature lock check).

---

## Storage

- `planwise/` directory, markdown files organized by status
- Issues: YAML frontmatter + markdown body
- Dependencies form a DAG — `pw ready` shows what's unblocked, `pw blocked` shows what's waiting
- File-based = version-controllable, diffable, greppable, LLM-readable

---

## CLI reference

`pw` (or `planwise`). JSON output by default, text with `-t`.

| Command | Description |
|---------|-------------|
| `init --project "name" --prefix "XX" [--agent claude\|cursor] [--rules python] [--layout python-web] [--no-vcs]` | Initialize planning + colocated jj+git (re-run with flags to update) |
| `create <feature\|sub-feature\|task\|uat\|bug> "title"` | Create issue (body via stdin) |
| `view <slug>` | View an issue |
| `edit <slug> --title/--body/--label/--agent` | Edit an issue |
| `status <slug> <status>` | Move to backlog/ready/in-progress/in-review/done |
| `close <slug> --reason "..."` | Close an issue |
| `list [type] [--status S] [--children-of slug]` | List with filters |
| `dep add/remove/list <slug> [dep-slug]` | Manage deps (cycle detection) |
| `ready [--children-of slug]` | Issues with all deps satisfied |
| `blocked [--children-of slug]` | Issues with unsatisfied deps |
| `next` | Pick the next issue to work on |
| `search "query"` | Search issues |
| `note <slug> "text"` | Add timestamped note |
| `stats` | Counts by status and type |
| `verify [--fix]` | Check integrity, auto-fix |
| `run <workflow> [args...] [--list] [--rules name] [--agent claude\|cursor]` | Output workflow template rendered for the target agent |
| `sync init / show / exec / state / reset` | Multi-step pipeline ops |

---

## License

MIT
