---
description: "Codebase evolution engine — optimize, fix, and verify code across 4 dimensions"
---

# Optimize — Codebase Evolution Engine

Hill-climbing to a local optimum: unified analysis finds both problems and opportunities, a self-adversarial challenge refines the plan before execution, fixes land first, then optimizations, the loop repeats on the same scope until nothing improves. Every change is verified by checks (typecheck/lint/test), committed on pass, reverted on fail. On a jj feature change — revert is free via the operation log.

## Dimensions

Each dimension is a **lens** — a distinct expert mindset for finding issues. The lens question is what the analyzer agent should hold in its head; the "what this lens reveals" list is what to look for; the "out of scope" list prevents overlap with other dimensions.

### Dimension 1: Safety
**Lens question:** "Where could this fail unexpectedly or be exploited?"

**What this lens reveals:**
- Missing input validation at system boundaries; trust assumptions that don't hold
- Edge cases (empty/None, boundary values, off-by-one, integer overflow)
- Race conditions, missing locks, unsafe shared state, unawaited coroutines, swallowed cancellation
- Swallowed or lost errors, bare excepts, inconsistent error semantics across call sites
- Resource leaks (file handles, sockets, connections, locks held outside context managers)
- Injection surfaces (SQL, shell, template, deserialization), secret/PII leakage in logs or errors
- Deprecated APIs with known security or correctness issues

**Out of scope for this lens:**
- Style and readability → Quality
- Module-level coupling → Structure
- Algorithmic cost → Performance

### Dimension 2: Quality
**Lens question:** "Could a new contributor read this in 5 minutes and understand intent?"

**What this lens reveals:**
- Cognitive complexity (deep nesting × control flow breaks — functions hard to reason about)
- Code smells (long method, large class, feature envy, data clumps, primitive obsession)
- Low signal density (verbose wrappers, redundant boilerplate, patterns that obscure intent)
- Duplication and near-duplicates differing only in names/constants
- Missing or leaky abstractions (logic that belongs in a shared function/class)
- Dead code (unreachable branches, unused imports/variables/functions, stale feature flags)
- Magic numbers and hardcoded strings scattered through logic
- Naming inconsistencies (same concept under different names; names that don't match behavior)
- Pattern inconsistencies (same operation implemented differently across call sites — the outlier is usually the drift; align to the majority pattern unless the majority is wrong)
- Convention violations relative to surrounding code or project rules

**Out of scope for this lens:**
- Module boundaries and inter-file structure → Structure
- Runtime cost of patterns → Performance
- Bugs that only fire in edge cases → Safety

### Dimension 3: Structure
**Lens question:** "If a likely future change lands here, how many files would have to move?"

**What this lens reveals:**
- Layering violations (domain logic in infrastructure; infrastructure in handlers)
- Circular or unnecessary dependencies between modules
- Change coupling (files that always change together reveal hidden dependencies)
- Afferent/efferent coupling extremes (too many dependents = fragile; too many dependencies = unstable)
- Low cohesion (classes/modules with split responsibilities — high LCOM)
- Connascence (shared assumptions between modules that make changes ripple)
- God classes/modules with too many responsibilities
- Missing or misplaced boundaries (logic that should live behind an interface/protocol)
- Coupling to concrete implementations where abstraction is warranted
- Deep inheritance hierarchies where composition is simpler
- Observability gaps at architectural boundaries (missing structured logging, metrics, tracing)

**Out of scope for this lens:**
- Within-function complexity → Quality
- Error handling correctness → Safety
- Latency or throughput characteristics → Performance

### Dimension 4: Performance
**Lens question:** "What's the hot path doing that it shouldn't?"

**What this lens reveals:**
- Hot paths with unnecessary allocations or copies
- Missing or incorrect caching (stale cache, unbounded growth, invalidation gaps)
- Suboptimal concurrency (event loop blocked by sync I/O, missing parallelism for independent I/O)
- O(n²) or worse algorithms where O(n log n) or O(n) alternatives exist
- Unnecessary serialization/deserialization round-trips
- Database query patterns (N+1 queries, missing indexes implied by patterns, unbounded result sets)
- Wasted I/O (reading the same file/key multiple times in one operation)

**Out of scope for this lens:**
- Resource leaks (correctness concern) → Safety
- Code duplication → Quality
- Module coupling → Structure


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

- **Issue slug** — `$ARGUMENTS` matches an existing issue slug.
  ```bash
  planwise view <slug>
  ```
  Read the issue. Extract file paths from its Implementation Notes — these are the scope.

- **Free text** — anything else. Resolve to files by searching the codebase (grep, glob, project structure). Use `AskUserQuestion` if ambiguous.

- **None** — no `$ARGUMENTS` provided. Default to changed files:
  ```bash
  jj diff --from dev@origin --name-only
  ```
  No changed files vs dev → stop.

Record: scope type, file list, initial file count.

## Phase 2: Baseline + snapshot

```bash
jj diff --from dev@origin --stat
BASELINE_OP=$(jj op log --limit 1 --no-graph -T 'id.short()')
echo "$BASELINE_OP" > .jj-optimize-baseline-op
```

Snapshot created via the jj operation log. If optimize goes wrong at any point: `jj op restore "$(cat .jj-optimize-baseline-op)" && rm .jj-optimize-baseline-op` — this rewinds the entire repo state (all changes made since the snapshot are undone atomically).

Verify checks pass before starting — don't optimize broken code:

Run the project's check command (typecheck, lint, test). If the project defines a `/check` command, use that. Otherwise, identify and run the appropriate commands for the project's language/framework.

If checks fail → stop. Fix first, then re-run `/optimize`.

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

$RULES

## Main Loop

### Phase 3: Discover (Analyze → Triage → Challenge inner loop)

The goal: produce the best possible plan before touching any code. Analysis, triage, and challenge form a tight inner loop — the challenger can trigger re-analysis when it discovers gaps.

`iteration++`. Snapshot: `pre_id=$(jj log -r @ --no-graph -T 'change_id.short()')`.
Initialize: `challenge_ledger = []` (persists across discovery cycles within this iteration).

#### Step 1: Analyze

Launch **4 subagents in one message** (one per dimension — Safety, Quality, Structure, Performance) — each reports BOTH findings (problems) AND proposals (opportunities):

```
[DIMENSION] analysis.

Adopt this dimension's lens and analyze the scope. Stay within the lens — items in the "out of scope" list belong to other agents and must not be reported here. Rules are not a discovery source; they constrain how fixes are written, not what to find.

Dimension lens:
[Paste only the relevant dimension's lens question, "what this lens reveals" list, and "out of scope" list from the Dimensions section above]

Scope: [type] | Context: [description]
Files: [list]
[If iteration 2+: "Ledger so far: [ledger entries for files in scope]"]
[If iteration 2+: "Skipped (do not re-report): [skipped set]"]
[If iteration 2+: "Failed (do not re-propose): [failed set]"]
[If re-analysis triggered by challenge: "Challenge context: [critique that triggered re-analysis, with evidence and new files added to scope]"]

Report TWO sections:

## Findings (problems to fix)
Issues, violations, bugs — things that are wrong and should be corrected.
[Per finding: severity (CRITICAL/HIGH/MEDIUM), title, @location, narrative]

## Proposals (opportunities to evolve)
Ways to make good code better — simpler, faster, safer, more accessible.
Only propose changes you are confident improve the code. No speculative "might help" proposals.
[Per proposal: title, @location, hypothesis, concrete change, expected impact]

Max 2 Explore subagents.
```

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

Launch a **challenger agent**:

```
Challenge this optimization plan. Your job is to find flaws, gaps, and missed opportunities that would make execution suboptimal. Be adversarial — assume the plan is wrong until proven otherwise.

## Current plan
[Full ordered plan: fixes first, then proposals, with file:region, severity, rationale for each]

## Raw analysis
[All findings + proposals from the 4 dimension agents, including ones triage dropped]

## Ledger context
[Ledger entries from previous iterations, skipped set, failed set]

## Challenge ledger
[Previous challenges + resolutions in this discovery cycle — do NOT re-raise resolved items]

Examine these angles:

1. **Root cause collapse** — are multiple findings symptoms of one cause? Identify the root and propose replacing N patches with 1 fix. Cite the specific findings by ID.
2. **Cascade prediction** — will fix A change code that fix B targets? Identify the dependency and propose reordering or merging.
3. **Redundancy elimination** — will any proposal become unnecessary after a specific fix lands? Cite which ones.
4. **Hidden connections** — do findings in different files share a common dependency (import, trait, type) that should also be in scope? Name the missing file(s). If found → flag as RE-ANALYZE.
5. **Assumption verification** — pick the 2-3 highest-impact plan items. Read the actual code at the cited locations. Does the finding/proposal actually hold? Flag any that don't survive code review.
6. **Simpler alternatives** — can multiple changes be achieved by 1 change at a different abstraction level? (e.g., fixing a shared utility instead of 3 call sites). If the alternative targets a file not yet analyzed → flag as RE-ANALYZE.
7. **Missed drops** — did triage keep anything that should be in `skipped`? (too risky, too vague, no concrete direction)

For each critique, report:

### Critique: [title]
**Type:** [root-cause-collapse | cascade | redundancy | hidden-connection | assumption-fail | simpler-alternative | missed-drop]
**Affects:** [plan item IDs]
**Evidence:** [what you read/verified]
**Proposed revision:** [concrete change to the plan]
**Re-analyze:** [YES — list new files to add to scope | NO]

If you find zero valid critiques after examining all 7 angles:
APPROVED — [one-line reasoning why the plan is sound]

Max 3 Explore subagents for assumption verification.
```

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

Dispatch fix agents sequentially — one per file (max 5 findings each).

```
Fix these findings in [path(s)].

[Per finding: #, title, severity, @location, narrative]
[Relevant ledger entries for this file: [entries]]

Rules:
- Do NOT modify test files and test fixtures — tests are the locked evaluator.
- Optimize for best code, not smallest diff. The result should read like it was written correctly from the start — not patched.
- Prefer deletions over additions. Added complexity must justify itself.
- No drive-by refactors.

Steps:
1. State hypothesis: what you expect and why.
2. Read target file + context (imports, callers, related files in the same module).
3. Follow the rules from the Rules section.
4. Fix. If multiple approaches work, pick the one that produces the cleanest result.
5. Self-verify: re-read your diff against the specific finding. For each finding you addressed:
   - Does the diff eliminate the exact issue described at @location? (re-read the changed code — is the problem gone?)
   - Does the fix follow the rules, or did you invent a different approach?
   - Did you change ONLY what's needed, or did scope creep in?
   If any answer is no, revise before reporting.
6. Report concisely — this flows back to the main agent's context:
   FIXED: [one-line hypothesis] | Files: [list] | Lines changed: [N]
   SKIPPED: [one-line reason] | Finding: #N
   PARTIAL: [one-line what remains] | Files: [list]
```

After each fix agent returns, **commit immediately** — jj's auto-snapshot has already captured the edits, and a committed change is cheaper and safer to reverse than uncommitted working-copy edits. Commit order is: capture restore-point → commit → run checks → restore on failure.

1. `jj diff --stat` — review net line delta. If additions significantly outweigh deletions, verify the added complexity is justified by the findings.
2. If stray edits outside the fix's scope landed in the working copy, split them out before committing: `jj split <file1> <file2> ...` to keep only intended files in the commit. Otherwise skip — explicit-path `jj commit` is unnecessary ceremony when the auto-snapshot already reflects the agent's edits.
3. Capture the op-id **before** committing so later rollback is deterministic regardless of any auto-snapshots check tools may trigger:
   ```bash
   PRE_COMMIT_OP=$(jj op log --limit 1 --no-graph -T 'id.short()')
   jj commit -m "optimize: fix [brief description]"
   ```
4. Run the project's check command (typecheck, lint, test). If the project defines a `/check` command or documents its check process in CLAUDE.md, use that. Otherwise, identify and run the appropriate commands for the project's language/framework.

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
```
Apply this improvement to [path(s)].

Proposal: [title, hypothesis, change description]
[Relevant ledger entries for this file: [entries]]

Rules:
- Do NOT modify test files and test fixtures — tests are the locked evaluator.
- The change must be a clear improvement — simpler, faster, safer, or more accessible.
- If after reading the code you realize the proposal won't improve things, report SKIP.

Steps:
1. Read target file + context.
2. Follow the rules from the Rules section above.
3. Apply the change.
4. Report concisely — this flows back to the main agent's context:
   APPLIED: [one-line what changed] | Files: [list]
   SKIP: [one-line why proposal doesn't hold up]
```

2. If SKIP → record in ledger, move to next proposal.

3. Capture the pre-commit op-id, then commit immediately (auto-snapshot captures the agent's edits). If stray non-proposal edits leaked in, `jj split` them out first:
   ```bash
   PRE_COMMIT_OP=$(jj op log --limit 1 --no-graph -T 'id.short()')
   jj commit -m "optimize: evolve — [proposal title]"
   ```

4. Run the project's check command (typecheck, lint, test). If the project defines a `/check` command, use that. Otherwise, identify and run the appropriate commands for the project's language/framework.

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
To undo all optimize changes: `jj op restore "$(cat .jj-optimize-baseline-op)" && rm .jj-optimize-baseline-op`

Next:  /next
Tip: /clear or /compact first if context is heavy.
```
