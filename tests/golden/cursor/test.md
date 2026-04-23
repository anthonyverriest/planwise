---
description: "Test writer — establishes behavioral contracts then tries to break them across up to 6 attack dimensions"
---

# Test Writer

Write tests that try to BREAK the code. Every test has a hypothesis: "I believe this will fail because…"

But you can't break what you haven't defined. **Stage 1** locks down the behavioral contract — what the code promises through its public API, its error handling, and its state transitions. **Stage 2** tries to violate that contract through adversarial probing across boundaries, race conditions, resource limits, auth bypass, state corruption, and malformed input. The functional tests are the measuring stick; the adversarial tests are the hammer.

**Assumed context:** this workflow runs inside a fresh jj workspace created by `pw claude`. Concurrent runs are isolated by workspace — each `pw claude` session has its own `@`. No cross-session contention.

## Deliverable

The output of this workflow is **new test files committed to the test bookmark**. Running existing tests and reporting their results is not the goal — writing new tests is. If the workflow ends without new test commits, it has failed.

## Production code lock

Agents MUST NOT modify non-test files (anything outside test directories and test modules). If the code under test has a real bug, document it — do not fix it. Repeat this rule in every agent prompt.

## Target: <the user's task>

## Stale-trunk check

If the current change is based on `dev@origin` and the remote has advanced, rebase first: `jj rebase -d dev@origin`. Rebase never blocks — jj records conflicts as data.

```bash
jj resolve --list
```

For each conflicted path: Read the file, `jj show` the trunk change that introduced the conflicting side to recover intent, then classify:
- Safe auto-merge region — pick the unified edit that satisfies both sides.
- Real logic collision — edit the file to a coherent unified result, preserving both intents where possible.

`jj status` must report no remaining conflicts before continuing.

## Phase 1: Resolve scope

**Base is `dev@origin`** All diffs and scope resolution use the `dev` bookmark on the remote.

- **Issue slug** — `<the user's task>` matches an existing issue slug.
  ```bash
  planwise view <slug>
  ```
  Read the issue. Extract file paths from its Implementation Notes — these are the scope.

- **Free text** — anything else. Resolve to files by searching the codebase (grep, glob, project structure). Ask the user if ambiguous: "I found N files matching '<the user's task>'. Which should I target?"

- **None** — no `<the user's task>` provided. Default to changed files:
  ```bash
  jj diff --from dev@origin --name-only
  ```
  No changed files vs dev → stop.

Record: scope type, file list, target description.

### Bookmark strategy

Tests commit to a bookmark, never directly to `dev`. Check if this target's test bookmark already exists (locally or on the remote):

```bash
jj bookmark list --all-remotes | grep "^test/<target-slug>\(@\|$\)"
```

- **Bookmark exists:** switch to it.
  ```bash
  jj edit test/<target-slug>
  ```
- **No bookmark yet:** create a new change off the current feature change (if on one) or off `dev@origin`, and anchor a bookmark:
  ```bash
  jj new -m "test: <target-slug>"
  jj bookmark create test/<target-slug> -r @
  ```

## Phase 2: Reconnaissance

### Step 1: Read the target

Read all files in scope. For each file, catalog:
- Public API surface (functions, protocols, methods) with signatures and return types
- Expected behavior per function — what it promises (happy path inputs → outputs)
- Input types and their validation (or lack thereof)
- Error contracts — what errors are documented/raised for known invalid inputs
- State transitions — valid states, transitions, and invariants the code maintains
- Async/concurrent boundaries, shared state, locks
- External dependencies (database, JWKS, HTTP clients)
- Existing tests (in test modules and test directories) — what is already covered?

**If the scope came from an issue slug:** also read the issue's Requirements and Acceptance Criteria. These define the behavioral contract the functional tests must verify.

### Step 2: Explore test infrastructure

Dispatch an **Explore subagent** to map the project's test infrastructure relevant to the target.

> Read `src/planwise/workflows/_test/explore.md` § **Test infrastructure exploration**.
> Inputs:
> - Target description: `<target description>`
> - File list in scope: `<paste>`
>
> Return per § **Return contract**.

The explore output feeds directly into the dimension agents (Phase 3) — they need to know what's testable before proposing attack vectors.

### Step 3: Research adversarial techniques (conditional)

**Only run this step when the target involves:** auth/access control, cryptography, payments/financial logic, user input handling, external API integration, or domains where the agent lacks deep expertise.

**Skip when the target is:** internal business logic, data transformers, pure utilities, CRUD operations, or well-understood patterns. The code recon from Steps 1-2 is sufficient.

When triggered, use `WebSearch` for expert adversarial testing techniques specific to the target's domain. Search angles to consider:

- **Domain-specific:** e.g., "adversarial testing [language] [framework] middleware", "chaos testing financial API idempotency", "JWT security edge cases penetration testing"
- **Language-specific:** e.g., "property-based testing boundary values [language]", "race condition testing patterns [framework]"
- **Attack pattern:** e.g., "OWASP API security testing checklist", "financial API abuse patterns"
- **Expert recommendations:** Search for recognized experts in the target's domain and what they recommend. Identify who the authorities are for the specific domain (fintech, auth, async systems, API security) and search for their talks, blog posts, or papers on testing strategies.

Extract concrete, actionable techniques. Discard generic advice. Record findings as attack vectors with code-level specifics. Attribute techniques to their source expert when applicable.

## Rules



## Phase 3: Test analysis

### Stage 1: Functional coverage

Before trying to break the code, define what "working" looks like. Dispatch a **functional analysis subagent**:

> Read `src/planwise/workflows/_test/analyze.md` § **Functional coverage analysis**.
> Inputs:
> - Target file list: `<paste>`
> - Scope: `<description>`
> - Recon catalog: `<Phase 2 Step 1 output — API surface, expected behaviors, error contracts, state transitions, existing test coverage>`
> - Test infrastructure: `<explore output from Phase 2 Step 2>`
> - Requirements and Acceptance Criteria (if from issue slug): `<paste or "N/A">`
>
> Return per § **Return contract (functional)**.

### Stage 2: Adversarial analysis

#### Dimension selection

Not every target warrants all 6 dimensions. Before launching agents, filter based on what the recon (Phase 2) revealed:

| Target characteristic | Skip dimension |
|---|---|
| No auth/access control in scope | Dimension 2: Auth & access control |
| No async, threading, or shared mutable state | Dimension 3: Concurrency & race conditions |
| No external-facing API (internal-only) | Dimension 4: Resource exhaustion & limits |
| No persistent state, no state machines | Dimension 5: State corruption & invariants |
| No external dependencies (DB, HTTP clients, queues) | Dimension 6: Error handling & dependency resilience (dependency half) |

Dimension 1 (Input abuse) always runs — every function has inputs. For small targets, use judgment to keep the dimension count proportional to the attack surface. Dimension descriptions live in `_test/analyze.md` § **Dimensions**.

Dispatch **one subagent per selected dimension in a single message** — each examines the target through its adversarial lens:

> Read `src/planwise/workflows/_test/analyze.md` § **Adversarial dimension analysis**, § **Dimensions**.
> Inputs:
> - Dimension: `<Dimension N: name>` (focus exclusively on this one)
> - Target file list: `<paste>`
> - Scope: `<description>`
> - Recon catalog: `<Phase 2 Step 1 output — API surface, input types, validation gaps, error paths, async boundaries, external dependencies, existing test coverage>`
> - Functional contract: `<Stage 1 output — the behavioral contract these tests will try to violate>`
> - Test infrastructure: `<explore output from Phase 2 Step 2>`
> - Research findings: `<relevant techniques from Phase 2 Step 3, or "Skipped — standard domain">`
>
> Return per § **Return contract (adversarial)**.

## Phase 4: Triage

1. **Collect** all test cases from Stage 1 (functional) and all attack vectors from Stage 2 (adversarial).
2. **Deduplicate** — same target:line across stages or dimensions → merge. Also check against existing test coverage from Phase 2 — drop items where an existing test already verifies the same behavior or probes the same failure mode. Re-examining covered code from a different adversarial angle is valuable; repeating the exact same test is not.
3. **Classify by test type:**
   - **Unit test** — pure function, no I/O → test module in target file.
   - **Integration test** — needs app context, middleware, or multiple components → project's integration test directory.
   - **Concurrency test** — needs threading or async runtime → integration tests with concurrent execution.
   - **Infrastructure-required** — needs database or external service → mark with skip/ignore annotation.
4. **Filter feasibility** — drop items that require infrastructure not available (e.g., property-based testing library not in dev dependencies, network simulation). Record as DEFERRED.
5. **Order:** functional tests first (they establish the baseline), then adversarial by severity: CRITICAL → HIGH → MEDIUM. Within severity: data integrity first, then auth, then state corruption, then input abuse, then concurrency, then resource limits, then error handling.

Initialize:

```
ledger = []          # {id, stage, dimension, title, hypothesis, severity, test_type, status, file, finding}
deferred = []        # items that need infrastructure not yet available
```

### Triage gate

Present the triaged test plan to the user:

```
Test triage for [target]:

  Functional:  N test cases (happy-path, error-contract, state-transition, integration)
  Adversarial: N attack vectors
    CRITICAL: N | HIGH: N | MEDIUM: N
  DEFERRED:    N items (missing infrastructure)

  Adversarial dimensions covered: [list]
  Adversarial dimensions skipped: [list + reason]
  Estimated total tests: N

Top 5 adversarial vectors:
  1. [SEVERITY] Title — Hypothesis: "..."
  2. ...
```

Use `AskQuestion` if available (fallback: ask in chat): **"N functional test cases + N adversarial vectors. Proceed with test writing, adjust, or stop here (report only)?"**

- **Proceed:** continue to Phase 5.
- **Adjust:** apply the user's changes to the vector list, then re-present.
- **Stop:** skip to Phase 7 (Report) with vectors and hypotheses only — no tests written.

## Phase 5: Write tests

Functional tests first (they establish the baseline), then adversarial. Dispatch test-writing agents sequentially — one per target file (unit tests) or per test file (integration tests).

### Stage 1 dispatch (functional)

> Read `src/planwise/workflows/_test/write.md` § **Functional tests**.
> Inputs:
> - Target file(s): `<paste>`
> - Bookmark: `<current bookmark>` (jj change id: `<current change id>`)
> - Test infrastructure: `<full explore output from Phase 2 Step 2>`
> - Test cases (ordered by type): `<for each case: id, title, behavior, type, target, test sketch>`
> - Rules: `<paste >`
>
> Return per § **Return contract (functional)**.

### Stage 2 dispatch (adversarial)

Max 8 attack vectors per agent.

> Read `src/planwise/workflows/_test/write.md` § **Adversarial tests**.
> Inputs:
> - Target file(s): `<paste>`
> - Bookmark: `<current bookmark>` (jj change id: `<current change id>`)
> - Test infrastructure: `<full explore output from Phase 2 Step 2>`
> - Functional tests already written: `<summary of Stage 1 tests — what contracts are locked down>`
> - Attack vectors (ordered by severity): `<for each vector: id, title, hypothesis, target, test sketch>`
> - Rules: `<paste >`
>
> Return per § **Return contract (adversarial)**.

**Handle agent status (both stages):**
- **BLOCKED:** Review the blocker. If it requires production code changes or new test infrastructure, record the items as DEFERRED with the reason. Do not stall the workflow.
- **SKIPPED items:** add to the `deferred` list with reason.

After each agent returns:

1. **Type check:**
   Run the project's type checker on the test code (e.g., `uv run mypy`).
   Fix type errors in test code only. If a fix requires changing production code, skip that test and record as DEFERRED.

2. **Run the new tests** (adapt command to what was written):
   - Unit tests: Run the relevant unit tests.
   - Integration tests: Run the relevant integration tests.

3. **Classify results** and update the ledger for each vector:
   - **Test passes** → code is robust against this vector. Update ledger: `status: pass`.
   - **Test fails with expected assertion** → potential bug found. Update ledger: `status: bug_found`, `finding: <failure details>`. Mark with the project's skip/ignore annotation and a descriptive reason (e.g., "KNOWN: <description>").
   - **Test fails with unexpected panic/crash** → deeper issue. Update ledger: `status: crash_found`, `finding: <crash details>`. Mark with the project's skip/ignore annotation (e.g., "CRASH: <description>").
   - **Test is flaky (passes sometimes)** → likely concurrency issue. Update ledger: `status: flaky`, `finding: <flaky behavior>`. Mark with the project's skip/ignore annotation (e.g., "FLAKY: <description>").

4. **Commit all tests** (passing + skip/ignore-annotated). Ignored tests document findings and won't break CI:
   ```bash
   jj commit <test_files_only> -m "test: [functional|adversarial] tests for [target] — [summary]"
   ```
   Pass explicit test paths to `jj commit` so non-test files remain in the working copy and are excluded from this commit. If non-test edits crept into the working copy, `jj restore <non-test-paths>` them first.

### Anchor the bookmark

After all test commits land, advance `test/<target-slug>` to the stack tip so the epilogue's `jj git push` publishes every test commit, not just the first. The revset picks the highest non-empty change in `dev@origin..@`:

```bash
TEST_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
jj bookmark set test/<target-slug> -r "$TEST_HEAD"
```

`jj bookmark set` rejects non-fast-forward moves without `--allow-backwards`. If rejected, investigate — do not force.

## Phase 6: Verify

Run the project's full typecheck, lint, and test suite.

- **All green** → proceed to report.
- **Failures in adversarial tests** → type errors: fix the test. Assertion failures in skip/ignore-annotated tests: expected, verify annotation is correct.
- **Failures in existing tests** → you broke something. Revert the last commit, investigate, rewrite.

## Phase 7: Report

Populate from the `ledger` and `deferred` lists. Each section maps directly to ledger fields.

```markdown
# Test Report

## Scope
[target description, file count, bookmark]

## Research
[Key expert techniques discovered and applied from WebSearch, or "Skipped — standard domain" if Phase 2 Step 3 was not run]

## Summary
Functional: N test cases written | Adversarial: N vectors analyzed, N tests written | Bugs found: N | Crashes: N | Deferred: N

## Functional Coverage
| Type | Test Cases | Pass |
|---|---|---|
| Happy path | N | N |
| Error contract | N | N |
| State transition | N | N |
| Integration contract | N | N |
| Boundary value | N | N |

## Adversarial Coverage
| Dimension | Vectors | Tests | Pass | Bug | Crash | Flaky | Deferred |
|---|---|---|---|---|---|---|---|
| [Only include rows for dimensions that were analyzed] |
| Input Abuse | N | N | N | N | N | N | N |
| ... | | | | | | | |

Dimensions skipped: [list with reason, or "None"]

## Bugs Found
### [SEVERITY] Title
**Dimension:** [dim] | **File:** @path:line
**Hypothesis:** [what the test proved]
**Evidence:** [test name, failure output]
**Impact:** [what could go wrong in production]
**Suggested fix direction:** [one-line hint — do NOT implement]

## Crashes Found
### Title
**File:** @path:line
**Trigger:** [what input/condition caused the panic]
**Stack:** [relevant panic message]

## Deferred
### Title
**Stage:** [functional | adversarial] | **Reason:** [why it couldn't be tested now]
**Prerequisite:** [what needs to be added — e.g., property-based testing library in dev dependencies, docker in CI]

## What Held Up
[Strong defensive patterns the analysis validated — worth preserving]

## Checks
typecheck: P/F | lint: P/F | test: P/F

Next:  /next
Tip: /clear or /compact first if context is heavy.
```
