---
description: "Codebase evolution engine — optimize, fix, and verify code across 4 dimensions"
---

# Optimize — Codebase Evolution Engine

Hill-climbing to a local optimum: unified analysis finds both problems and opportunities, a self-adversarial challenge refines the plan before execution, fixes land first, then optimizations, the loop repeats on the same scope until nothing improves. Every change is verified by checks (typecheck/lint/test), committed on pass, reverted on fail. On a jj feature change — revert is free via the operation log.

**Assumed context:** this workflow runs inside a fresh jj workspace created by `pw claude`. Concurrent runs are isolated by workspace — each `pw claude` session has its own `@`. No cross-session contention.

## Dimensions

Four lenses run in parallel during analysis: **Safety**, **Quality**, **Structure**, **Performance**. Each is a distinct expert mindset with its own lens question, "what this lens reveals" list, and "out of scope" list. Full definitions live in `src/planwise/workflows/_optimize/analyze.md § **Dimensions**` — the analyzer subagents read them directly.

## Evaluator lock

Tests are the evaluator. Agents MUST NOT modify test files and test fixtures (e.g., `tests/`, `__tests__/`, `*_test.*`, `*.spec.*`, and any test helper/fixture files). If a change breaks tests, the change is wrong — not the tests. Repeat this rule in every agent prompt.

## Stale-trunk check

If the current feature change is based on `dev@origin` and the remote has advanced, rebase before optimizing: `jj rebase -d dev@origin`. Rebase never blocks — jj records conflicts as data.

After rebase, check for conflicts:
```bash
jj resolve --list
```

For each conflicted path: Read the file, `jj show` the trunk change that introduced the conflicting side to recover intent, then classify:
- **Mechanical** (imports, formatting, non-overlapping additions, one-side deletes) → resolve inline.
- **Semantic** (both sides changed the same logic with different intent) → STOP, show the user the conflicted paths and both sides, ask which intent to keep. Do not guess.

`jj status` must report no remaining conflicts before continuing.

## Phase 1: Resolve scope

**Base is `dev@origin`** All diffs, comparisons, and scope resolution use the `dev` bookmark on the remote.

- **Issue slug** — `<ARGS>` matches an existing issue slug.
  ```bash
  planwise view <slug>
  ```
  Read the issue. Extract file paths from its Implementation Notes — these are the scope.

- **Free text** — anything else. Resolve to files by searching the codebase (grep, glob, project structure). Ask the user if ambiguous.

- **None** — no `<ARGS>` provided. Default to changed files:
  ```bash
  jj diff --from dev@origin --name-only
  ```
  No changed files vs dev → stop.

Record: scope type, file list, initial file count.

## Phase 2: Baseline + snapshot

```bash
jj diff --from dev@origin --stat
BASELINE_OP=$(jj op log --limit 1 --no-graph -T 'id.short()')
echo "$BASELINE_OP" > "$(jj root)/.jj/optimize-baseline-op"
```

Snapshot created via the jj operation log. The sentinel lives under `.jj/` — jj's metadata directory is excluded from the working copy, so it is never snapshotted into a commit. If optimize goes wrong at any point: `jj op restore "$(cat "$(jj root)/.jj/optimize-baseline-op")" && rm "$(jj root)/.jj/optimize-baseline-op"` — this rewinds the entire repo state (all changes made since the snapshot are undone atomically).

Verify the project's typecheck, lint, and test commands pass before starting — don't optimize broken code. If they fail → stop. Fix first, then re-run `/optimize`.

Initialize:

```
ledger = []          # {id, file, region, action, rationale, stage, outcome, affected_files}
skipped = set()      # findings that can't be auto-fixed (manual-only)
failed = set()       # proposals/fixes that failed checks
iteration = 0
total_commits = 0
scope = initial_file_list
```

## Convergence

No hard caps. No subjective scoring. Convergence is the **only** termination signal.

**Mechanism:** snapshot `pre_id=$(jj log -r @ --no-graph -T 'change_id.short()')` before each iteration. After all fixes and evolutions are applied: `post_id=$(jj log -r @ --no-graph -T 'change_id.short()')`.

- `pre_id == post_id` → nothing landed → converged → exit.
- Triage produces empty plan (all findings in `skipped` or `failed`) → stuck → exit.

**Cost checkpoint:** after `ceil(initial_file_count / 3, min=5)` cumulative commits, pause and report progress to the user. User decides: continue or stop. Reset counter on continue.

**Conflict detection:** if a fix modifies a region that a previous evolution changed (or vice versa), that's a conflict — surface it to the user, don't loop on it.

---

## Rules



## Main Loop

### Phase 3: Discover (Analyze → Triage → Challenge inner loop)

The goal: produce the best possible plan before touching any code. Analysis, triage, and challenge form a tight inner loop — the challenger can trigger re-analysis when it discovers gaps.

`iteration++`. Snapshot: `pre_id=$(jj log -r @ --no-graph -T 'change_id.short()')`.
Initialize: `challenge_ledger = []` (persists across discovery cycles within this iteration).

#### Step 1: Analyze

Launch **4 subagents in one message** (one per dimension — Safety, Quality, Structure, Performance). Each reports BOTH findings (problems) AND proposals (opportunities).

For each dimension, dispatch:

> Read `src/planwise/workflows/_optimize/analyze.md` § **Dimension analysis**, § **Dimensions**.
> Inputs:
> - Dimension: `<Safety | Quality | Structure | Performance>`
> - Scope type: `<type>`
> - Context: `<description>`
> - Files: `<list>`
> - Ledger (iteration 2+): `<entries for files in scope, or "None">`
> - Skipped — do not re-report (iteration 2+): `<set, or "None">`
> - Failed — do not re-propose (iteration 2+): `<set, or "None">`
> - Challenge context (if re-analysis triggered): `<critique + evidence + new files, or "None">`
> - Rules: `<paste >`
>
> Return per § **Return contract**.

#### Step 2: Triage

1. **Deduplicate** — same file:region across dimensions → merge, keep highest severity.
2. **Conflict detection** — same file:region has both a finding AND a proposal → finding takes priority, proposal is deferred (will execute after fix lands).
3. **Ledger check** — drop anything already in `skipped` or `failed`.
4. **Classify findings** — auto-fixable (S/M effort, concrete direction, no API/schema changes) vs manual-only (L effort, needs decisions/user input). Manual-only → `skipped`.
5. **Order the plan:**
   - **Fixes first:** CRITICAL → HIGH → MEDIUM. Within same severity: Safety findings first (correctness/exploitability), then Quality, Structure, Performance. Then S before M → line desc. Group by file.
   - **Proposals second:** ordered by confidence and expected impact.
6. **Empty plan check** — if zero auto-fixable findings AND zero viable proposals → converged, skip to Phase 7 (Report).

#### Step 3: Challenge

Dispatch a challenger agent:

> Read `src/planwise/workflows/_optimize/challenge.md` § **Challenger**.
> Inputs:
> - Current plan: `<full ordered plan — fixes first, then proposals, with file:region, severity, rationale>`
> - Raw analysis: `<all findings + proposals from the 4 dimension agents, including ones triage dropped>`
> - Ledger context: `<ledger entries from previous iterations, skipped set, failed set>`
> - Challenge ledger: `<previous critiques + resolutions in this discovery cycle, or "None">`
>
> Return per § **Return contract**.

#### Step 4: Process challenger response

- **APPROVED** → discovery converged. Proceed to Phase 4.
- **Critiques found:**
  1. For each critique, verify it's valid (not a repeat from `challenge_ledger`, evidence checks out).
  2. Apply valid critiques to revise the plan:
     - Root cause collapse → replace N items with 1, adjust ordering.
     - Cascade → reorder or merge affected items.
     - Redundancy → mark redundant items as "deferred pending [fix ID]".
     - Hidden connection → add file(s) to scope.
     - Assumption fail → drop the item, add to `skipped` with reason "assumption invalid".
     - Simpler alternative → replace N items with the simpler approach.
     - Missed drop → move to `skipped`.
  3. Record each critique + resolution in `challenge_ledger`.
  4. **If any critique flagged RE-ANALYZE:** add new files to scope → return to Step 1 (re-analyze with expanded scope and challenge context). The 4 dimension agents see what the challenger found, producing targeted findings for the new files.
  5. **If no RE-ANALYZE:** return to Step 3 (re-challenge the revised plan).

#### Discovery convergence
- Challenger says APPROVED → proceed to Phase 4.
- Revised plan equals input plan (no critiques produced changes) → proceed to Phase 4.
- Challenge ledger shows a contradiction (critique reverses a previous resolution) → **stop discovery**, proceed to Phase 4 with current plan. Log the contradiction for the report.

### Phase 4: Execute fixes

Dispatch fix agents sequentially — one per file (max 5 findings each):

> Read `src/planwise/workflows/_optimize/execute.md` § **Fix**.
> Inputs:
> - Target file(s): `<path(s)>`
> - Findings: `<per finding — #, title, severity, @location, narrative>`
> - Relevant ledger entries for this file: `<entries, or "None">`
> - Rules: `<paste >`
>
> Return per § **Return contract (fix)**.

After each fix agent returns, **commit immediately** — jj's auto-snapshot has already captured the edits, and a committed change is cheaper and safer to reverse than uncommitted working-copy edits. Commit order is: capture restore-point → commit → run checks → restore on failure.

1. `jj diff --stat` — review net line delta. If additions significantly outweigh deletions, verify the added complexity is justified by the findings.
2. If stray edits outside the fix's scope landed in the working copy, split them out before committing: `jj split <file1> <file2> ...` to keep only intended files in the commit. Otherwise skip — explicit-path `jj commit` is unnecessary ceremony when the auto-snapshot already reflects the agent's edits.
3. Capture the op-id **before** committing so later rollback is deterministic regardless of any auto-snapshots check tools may trigger:
   ```bash
   PRE_COMMIT_OP=$(jj op log --limit 1 --no-graph -T 'id.short()')
   jj commit -m "optimize: fix [brief description]"
   ```
4. Run the project's typecheck, lint, and test commands.

**Pass:** record in ledger with outcome `committed` and list `affected_files`. Increment `total_commits`.

**Fail:** dispatch targeted fix agent with same rules (including evaluator lock). The retry agent's edits land in the current working-copy change (`@`, the empty change jj created after your commit). Re-run checks.
- **Pass on retry:** amend the original commit with the follow-up edits:
  ```bash
  jj squash   # moves @ into @-, leaving a single commit with combined edits
  ```
  Record in ledger as `committed`.
- **Still fails:** restore the repo to the exact state from before the commit:
  ```bash
  jj op restore "$PRE_COMMIT_OP"
  ```
  This reverses the commit, the retry-agent edits, and any check-tool auto-snapshots atomically. Record in ledger with outcome `reverted`, add to `failed`.

SKIPPED findings → add to `skipped`.

### Phase 5: Execute proposals

For each proposal from the triage plan (one at a time, sequentially):

1. Dispatch an evolution agent (the challenge phase already ordered fixes before proposals — the agent reads the post-fix code and self-corrects if the proposal no longer applies):

   > Read `src/planwise/workflows/_optimize/execute.md` § **Evolve**.
   > Inputs:
   > - Target file(s): `<path(s)>`
   > - Proposal: `<title, hypothesis, change description>`
   > - Relevant ledger entries for this file: `<entries, or "None">`
   > - Rules: `<paste >`
   >
   > Return per § **Return contract (evolve)**.

2. If SKIP → record in ledger, move to next proposal.

3. Capture the pre-commit op-id, then commit immediately (auto-snapshot captures the agent's edits). If stray non-proposal edits leaked in, `jj split` them out first:
   ```bash
   PRE_COMMIT_OP=$(jj op log --limit 1 --no-graph -T 'id.short()')
   jj commit -m "optimize: evolve — [proposal title]"
   ```

4. Run the project's typecheck, lint, and test commands.

5. **Pass:** record in ledger with outcome `committed` and `affected_files`. Increment `total_commits`.

6. **Fail:** restore the repo to the exact pre-commit state:
   ```bash
   jj op restore "$PRE_COMMIT_OP"
   ```
   Record in ledger with outcome `reverted`, add to `failed`. Move to next proposal.

### Phase 6: Converge or continue

`post_id=$(jj log -r @ --no-graph -T 'change_id.short()')`.

- `pre_id == post_id` → nothing landed → **converged**. Go to Phase 7.
- **Cost checkpoint:** if `total_commits >= ceil(initial_file_count / 3, min=5)` since last checkpoint → report progress to user. User says stop → go to Phase 7. User says continue → reset checkpoint counter.
- Return to Phase 3 (same scope — ledger prevents redundant work).

---

## Phase 7: Report

Collect finding/proposal counts from the first analysis (iteration 1) and final state.

```markdown
# Optimization Report

## Scope
[type, initial file count, modules/packages, bookmark]

## Summary
[2-3 sentences]
Iterations: N | Fixed: N | Evolved: N | Remaining: N
Challenge: N plan revisions across iterations (N root-cause collapses, N cascade reorders, N dropped assumptions)
Termination: converged | stuck (only skipped/failed remain) | user stopped

## Findings
| Dimension | Initial | Remaining |
|---|---|---|
| Safety | N | N |
| Quality | N | N |
| Structure | N | N |
| Performance | N | N |

## Fixed
### [SEVERITY] Title
**Dim:** [dim] | **Location:** @path | **Changed:** [one-line]

## Evolved
### Proposal title
**Dim:** [dim] | **Location:** @path | **Hypothesis:** [one-line] | **Result:** [what improved]

## Remaining

### [SEVERITY] Title
**Dim:** [dim] | **Effort:** S/M/L | **Location:** @path:line
**Why not fixed:** [reason — skipped (manual-only) | failed (checks broke) | conflict (user deferred)]
[Direction]

## What Looks Good
[Strong patterns per dimension]

## Verdict
CONVERGED (no remaining) | STUCK (skipped/manual-only remain) | STOPPED (user halted at checkpoint)

## Checks
typecheck: P/F | lint: P/F | test: P/F

## Rollback
To undo all optimize changes: `jj op restore "$(cat "$(jj root)/.jj/optimize-baseline-op")" && rm "$(jj root)/.jj/optimize-baseline-op"`

Next:  /next
Tip: /clear or /compact first if context is heavy.
```
