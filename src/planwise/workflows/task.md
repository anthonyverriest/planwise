---
description: "Execute a task — implement, test, optimize, and memo in one pass"
---

# Task — Single-Pass Execution

Implement a task issue following its spec, then test, optimize, and update the knowledge base. One pass, no subagents.

## Target: $ARGUMENTS

## Step 1: Read the task

```bash
planwise view $ARGUMENTS
```

**Lock check** — if this task is already `in-progress`, stop:
```bash
planwise view $ARGUMENTS --field status
```
If status is `in-progress`, STOP: `Task $ARGUMENTS is already being implemented. Coordinate before proceeding.`

Read the full spec: What & Why, Requirements, Edge Cases, Constraints, Scope, Implementation Notes, Acceptance Criteria.

Move to in-progress:

```bash
planwise status $ARGUMENTS in-progress
```

## Step 1.5: Base the task change

Work **anonymously via change-id** during iteration — a named bookmark is only anchored at the end (Step 7). If the task is abandoned, no bookmark churn.

Check if an in-progress task change for this slug already exists (from a previous `/task` run). Tasks are identified by the slug suffix `(#$ARGUMENTS)` in their description; select the latest one not yet merged into `dev@origin`:

```bash
jj log -r 'description(glob:"*(#'"$ARGUMENTS"')*") & ~::dev@origin' --limit 1 -T 'change_id.short()'
```

- **Change exists:** switch to it.
  ```bash
  jj edit <change-id>
  ```

- **No change yet:** create a new change. If `@` is already on a feature change (descended from `dev@origin` but not equal to it), branch off `@` so the task lands on the feature. Otherwise, base off the latest `dev`.
  ```bash
  jj git fetch
  # On a feature change? (check returns non-empty if @ is a descendant of dev@origin but not dev@origin itself)
  jj log -r '@ & (dev@origin..)' --no-graph -T 'change_id.short()'
  # If non-empty: jj new -m "<type>: <short description> (#$ARGUMENTS)"
  # If empty:     jj new dev@origin -m "<type>: <short description> (#$ARGUMENTS)"
  ```

Record a kebab-case topic derived from the task title — used in Step 7 as the bookmark name.

**Stale-trunk check:** if this task change is based on `dev@origin` and the remote has advanced (`jj git fetch` pulled new commits), rebase before working: `jj rebase -d dev@origin`. jj records conflicts as data, so rebase does not fail mid-flight.

After rebase, check for conflicts:
```bash
jj resolve --list
```

For each conflicted path: Read the file, `jj show` the trunk change that introduced the conflicting side to recover intent, then classify:
- **Mechanical** (imports, formatting, non-overlapping additions, one-side deletes) → resolve inline.
- **Semantic** (both sides changed the same logic with different intent) → STOP, show the user the conflicted paths and both sides, ask which intent to keep. Do not guess.

`jj status` must report no remaining conflicts before continuing.

## Step 1.6: Planning-lessons lookup

Before implementing, check `_lessons.md` for relevant planning lessons produced by `/memo` Phase 6.

```bash
test -f planwise/knowledge/_lessons.md && grep -i -B1 -A5 "<domain-tag-or-keyword-from-spec>" planwise/knowledge/_lessons.md
```

Match by `trigger` field (domain tag, file glob, or keyword set drawn from the task's Scope and Implementation Notes). If no file or no match, skip silently. Ignore any hit whose context falls under the `## Archive` heading — those lessons are pruned and not active. For each hit, adjust implementation:
- **risk-miss** → treat the named assumption as already broken; verify explicitly before coding against it
- **approach-wrong** → do not use the rejected approach named in the lesson; pick the alternative it recommends
- **scope-miss** / **estimation-miss** / **quality-gap** → flag to the user if the lesson reveals work the spec didn't account for; do not silently expand scope

Task never writes to `_lessons.md` — production is reserved for `/memo` at the feature level, where convergence signals actually accumulate.

## Rules

$RULES

## Step 2: Implement

Read each file immediately before editing. Follow the rules above. Respect the spec's Constraints section — these are regressions that must not happen.

No scope creep — only modify files listed in the Scope section. If you believe an unlisted file needs changing, STOP and report to the user — do not modify it yourself.

If the spec has Implementation Notes, use them: follow the referenced patterns, target the specified files and locations. The pattern snippet shows the existing shape to replicate — trust the current code over a stale snippet if they diverge.

If the codebase doesn't match what the spec describes (files missing, patterns changed), STOP and report to the user. Do not implement against stale assumptions.

If the spec's approach is fundamentally flawed (not just a missing file — a wrong architectural assumption), STOP and report to the user: what the spec assumes, what's actually true, and a suggested alternative. Do not implement a known-bad approach.

If after implementing you have concerns about fragility, correctness, or unintended side effects — ask the user before proceeding to tests. Describe the concern and let them decide whether to continue, adjust, or stop. Proceeding silently with a known concern is worse than pausing.

For bug fixes:
- Trace the bad value backward through the call stack to the origin.
- Fix at the root cause, not where the symptom appears.
- If 3 fix attempts fail, stop and re-examine the architecture. Report findings to the user instead of trying a 4th fix.

## Test Rules

$TESTRULES

## Step 3: Test

Follow the Test Rules above (`Contract:`/`Hypothesis:` docstrings, helper reuse, mock fidelity, production code lock).

### Functional tests

Write tests that verify the Requirements and Edge Cases from the spec. Cover these categories:
- **Happy paths:** primary use cases with valid inputs → expected outputs
- **Error contracts:** expected error behavior for known invalid inputs
- **State transitions:** valid state changes produce correct results, invariants hold
- **Integration contracts:** components interact correctly at boundaries (caller → callee, request → response shape)
- **Boundary values:** min/max of accepted ranges, empty-but-valid inputs

Prioritize untested public API surface — at most 10 functional test cases.

### Adversarial pass

Do NOT skip this pass with "functional tests passed, this task is small." Adversarial probes target a different failure class than functional tests — passing functional ≠ robust.

For each file modified, probe **input abuse** — try to break the code:

- Boundary values (0, -1, max, empty string, None)
- Malformed input (wrong types, unexpected shapes, oversized)
- Special characters (unicode, injection payloads if user-facing)
- Denormalized strings (whitespace-only, zero-width chars, null-equivalent)

Skip the other adversarial dimensions (auth, concurrency, resource exhaustion, state corruption, error resilience) — those are for `/test` on features.

If a test exposes a real bug, fix it. If the fix is out of scope, document it in a note on the task issue and mark the test with the project's skip annotation.

### Bug fix verification

For bug fixes: demonstrate the test fails without the fix and passes with it. This is the proof that the fix is correct.

### Run validation and checks

If the spec's Implementation Notes includes a Validation command, run it first — this is the spec-specific verification (may differ from the project's general checks).

Then run the project's typecheck, lint, and test commands.

If they fail, fix and re-run. If a failure is in code you didn't write, stop and report.

### Acceptance criteria self-check

Before committing, re-read the spec's Acceptance Criteria. Verify each criterion against the code you wrote — read the actual code, don't rely on memory. If any criterion is not satisfied, fix it now.

## Step 4: Commit

```bash
jj commit -m "<type>: <description> (#$ARGUMENTS)"
```

jj auto-snapshots the working copy — no staging. `jj commit` closes the current change and starts a new empty one on top.

Commit types: feat, fix, ref, test, docs, chore, style. Use imperative mood, focus on outcomes.

## Step 5: Optimize (single pass)

One analysis pass over the files you modified — no convergence loop. Optimize for best code, not smallest diff — the result should read like it was written correctly from the start, not patched. Prefer deletions over additions — added complexity must justify itself.

### Evaluator lock

Do NOT modify test files. If a change breaks tests, the change is wrong.

### Analyze

Do NOT collapse the 4 lenses into one with "diff is small, only Quality matters here." Each lens targets a distinct bug class — Safety catches leaks, Structure catches layering drift, Performance catches hot-path regressions. Skipping lenses is how production bugs leak through single-pass reviews.

Read each file you modified. Walk these 4 lenses (one pass, no subagents):

**Safety** — "Where could this fail unexpectedly?"
- Resource leaks (unclosed handles, connections outside context managers)
- Blocking calls in async context, swallowed errors
- Missing error handling at boundaries
- Edge cases not handled (empty/None, boundary values)

**Quality** — "Could a new contributor read this in 5 minutes?"
- Cognitive complexity (deep nesting, long functions, control flow breaks hard to reason about)
- Low signal density (verbose wrappers, redundant boilerplate, patterns that obscure intent)
- Duplication with existing code (did you reinvent a utility that exists?)
- Missing or leaky abstractions (logic that belongs in a shared function/class)
- Dead code (unused imports, unreachable branches, stale variables)
- Magic numbers or hardcoded strings (should be named constants)
- Naming inconsistencies with surrounding code
- Convention violations (rules above)

**Structure** — "If a future change lands here, how many files would have to move?"
- Layering violations (domain logic in infrastructure, infrastructure in handlers)
- Circular dependencies introduced by new imports

**Performance** — "What's the hot path doing that it shouldn't?"
- Suboptimal algorithms (O(n²) where O(n) or O(n log n) exists, N+1 queries)

### Fix

If issues are found: fix them. After fixing, self-verify — re-read your diff and check:
- Is the problem actually gone? (re-read the changed code)
- Did you follow the rules, or invent a different approach?
- Did you change ONLY what's needed, or did scope creep in?

If any answer is no, revise before proceeding.

Re-run checks. If checks pass, commit separately — pass explicit paths so unrelated working-copy edits stay out of this commit:
```bash
jj commit <modified-files> -m "optimize: <what was improved> (#$ARGUMENTS)"
```

If checks fail after an optimize fix, revert the change (`jj restore <files>`) and move on. Do not loop.

If no issues are found or all are trivial: skip. Do not optimize for the sake of optimizing.

## Step 6: Memo (conditional)

**Skip this step if** no knowledge base exists (`planwise/knowledge/` is empty or absent).

If the task touched a domain that has an existing knowledge file:

```bash
cat planwise/knowledge/<domain>.md
# or, for targeted retrieval:
grep -n '^## [0-9]' planwise/knowledge/<domain>.md  # section TOC with line numbers
# then read only affected sections by offset
```

Check if the task:
- Invalidated an existing gotcha (you fixed the root cause)
- Changed a pattern (new approach replaces old)
- Added a new constraint or decision worth recording
- Revealed a new gotcha
- Changed the architecture (new component, restructured data flow, moved responsibilities)
- Changed connections (new dependency, new consumer, new shared types)

If yes, update the domain file inline — no subagents. Writing principles:
- **Density without compression:** every sentence carries information — no filler, no hedging. But don't sacrifice clarity for brevity.
- **Evergreen language:** present tense, no temporal references ("recently", "after this task"), no feature-specific framing
- **Concrete over abstract:** name specific files, functions, types — not vague descriptions. "The webhook handler validates idempotency keys" not "The system ensures idempotent processing."
- **Self-contained entries:** each entry stands alone with its rationale inline — a reader should never need to chase other sources
- **Entry quality minimum:** every entry must name at least one specific file, function, or type. If an entry could apply to any codebase, it's too abstract — rewrite or skip it.
- **Signal salience:** mark load-bearing entries `[critical]` — decisions, constraints, or gotchas where getting it wrong causes a production incident, data loss, or security vulnerability. Use sparingly.
- **Link entries:** when a decision is motivated by a constraint, or a pattern prevents a gotcha, say so inline: "Motivated by: *[entry name]*" or "Prevents: *[entry name]*."

Remove entries the task made obsolete. After any removal or update, check for dangling cross-references — if another entry says `Motivated by:`, `Prevents:`, or `Motivated:` pointing to the removed/changed entry, fix or remove the reference.

Then update the index if it exists:

```bash
grep -i "<domain>" planwise/knowledge/INDEX.md
```

If the domain file's summary, tags, or entry titles changed, update the corresponding block in `INDEX.md`. Maintain alphabetical order.

If no updates needed, skip.

## Step 7: Anchor bookmark, close, and report

Anchor the named bookmark on the task head. Use a revset to find it robustly:

```bash
TASK_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
# Prefix: task/ for regular tasks, fix/ if the task is a bug fix.
jj bookmark create task/<topic> -r "$TASK_HEAD" || jj bookmark set task/<topic> -r "$TASK_HEAD"
```

`jj bookmark set` rejects non-fast-forward moves without `--allow-backwards`. If rejected, investigate — do not force.

Mark the task done:

```bash
planwise status $ARGUMENTS done
```

```
Task $ARGUMENTS complete.

What was done:
- [Summary of changes]

Files changed: [list]
Tests: [N] functional + [N] adversarial, all passing
Optimize: [what was improved, or "clean — no issues found"]
Knowledge: [domain file updated / skipped]
Checks: typecheck P/F | lint P/F | test P/F

Retrospective: [one sentence — what assumption was wrong or what you'd do differently, or "smooth — no surprises"]

Bookmark: task/<topic> (head: $TASK_HEAD)

Next steps:
1. Push: jj git push --bookmark task/<topic>
2. Open the PR: gh pr create --base dev --head task/<topic> --title "<title>" --body "Closes #$ARGUMENTS"
```
