---
description: "Test writer — establishes behavioral contracts then tries to break them across up to 6 attack dimensions"
---

# Test Writer

Write tests that try to BREAK the code. Every test has a hypothesis: "I believe this will fail because…"

But you can't break what you haven't defined. **Stage 1** locks down the behavioral contract — what the code promises through its public API, its error handling, and its state transitions. **Stage 2** tries to violate that contract through adversarial probing across boundaries, race conditions, resource limits, auth bypass, state corruption, and malformed input. The functional tests are the measuring stick; the adversarial tests are the hammer.

## Deliverable

The output of this workflow is **new test files committed to the branch**. Running existing tests and reporting their results is not the goal — writing new tests is. If the workflow ends without new test commits, it has failed.

## Production code lock

Agents MUST NOT modify non-test files (anything outside test directories and test modules). If the code under test has a real bug, document it — do not fix it. Repeat this rule in every agent prompt.

## Target: $ARGUMENTS

## Phase 1: Resolve scope

**Base branch is `dev`** All diffs and scope resolution use `dev`.

- **Issue slug** — `$ARGUMENTS` matches an existing issue slug.
  ```bash
  planwise view <slug>
  ```
  Read the issue. Extract file paths from its Implementation Notes — these are the scope.

- **Free text** — anything else. Resolve to files by searching the codebase (grep, glob, project structure). Use `AskUserQuestion` if ambiguous: "I found N files matching '$ARGUMENTS'. Which should I target?"

- **None** — no `$ARGUMENTS` provided. Default to changed files:
  ```bash
  git diff dev --name-only
  ```
  No changed files vs dev → stop.

Record: scope type, file list, target description.

### Branch strategy

Tests commit to a branch, never directly to `dev`. Check if a test branch exists:

```bash
git branch --list 'test/*'
```

- **Branch exists:** switch to it.
- **No branch yet:** create one from the current feature branch (if on one) or from `dev`:
  ```bash
  git checkout -b test/<target-slug>
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

Launch an **Explore subagent** to map the project's test infrastructure relevant to the target:

```
Explore the test infrastructure for [target description].

Find and read:
- Shared test helpers, fixtures, factories, builders
- Request/response utilities and test clients
- Conftest files, setup/teardown patterns
- Existing tests for the target files (or similar modules)
- Available test dependencies (property-based testing libs, faker, etc.)

Report:
- Reusable helpers with their signatures and import paths
- Assertion patterns and conventions used in existing tests
- What test types are supported (unit, integration, async, concurrency)
- Available fixture/factory patterns with code snippets
- Test infrastructure gaps — what CAN'T be tested with current tooling
```

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

$TESTRULES

## Phase 3: Test analysis

### Stage 1: Functional coverage

Before trying to break the code, define what "working" looks like. Launch a **functional analysis subagent**:

```
Functional coverage analysis.

Target: [file list]
Scope: [description]
Recon catalog: [Phase 2 Step 1 output — API surface, expected behaviors, error contracts, state transitions, existing test coverage]
Test infrastructure: [explore output from Phase 2 Step 2]
[If from issue slug: "Requirements and Acceptance Criteria: [from the issue]"]

Analyze the target's public API and identify test cases that verify the behavioral contract. You are defining what "working correctly" means — the adversarial stage will then try to violate it.

IMPORTANT: Do NOT modify any non-test files. You are analyzing, not fixing.

For each test case, report:

### Test: [title]
**Behavior:** [what the code promises — expected input → expected output/effect]
**Type:** happy-path | error-contract | state-transition | integration-contract
**Target:** @file:line
**Test sketch:** [2-3 line pseudocode]
**Needs:** [existing helper, new fixture, etc.]

Categories to cover:
- **Happy paths:** primary use cases with valid inputs → expected outputs
- **Error contracts:** documented/expected error behavior for known invalid inputs (not adversarial — these are errors the code explicitly handles)
- **State transitions:** valid state changes produce correct results, invariants hold
- **Integration contracts:** components interact correctly at boundaries (caller → callee, request → response shape)
- **Boundary values:** valid edges — min/max of accepted ranges, empty-but-valid inputs

Do not invent failure scenarios — that's Stage 2. Focus on what the code is SUPPOSED to do.
Report at most 10 test cases. Prioritize untested public API surface.
```

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

Dimension 1 (Input abuse) always runs — every function has inputs. For small targets, use judgment to keep the dimension count proportional to the attack surface.

Launch **one subagent per selected dimension in one message** — each examines the target through its adversarial lens:

```
[DIMENSION] adversarial analysis.

Target: [file list]
Scope: [description]
Recon catalog: [Phase 2 Step 1 output — API surface, input types, validation gaps, error paths, async boundaries, external dependencies, existing test coverage per file]
Functional contract: [Stage 1 output — the behavioral contract these tests will try to violate]
Test infrastructure: [explore output from Phase 2 Step 2 — available helpers, fixtures, supported test types, infrastructure gaps]
Research findings: [relevant techniques from Phase 2 Step 3, or "Skipped — standard domain" if Step 3 was not run]

You are trying to BREAK this code. The functional contract above defines what "working" looks like — find inputs, states, and conditions that violate it. Use the recon catalog as your starting point — do not re-read target files unless you need to examine a specific code path in detail.

IMPORTANT: Do NOT modify any non-test files. You are analyzing, not fixing.

For each attack vector you identify, report:

### Attack: [title]
**Hypothesis:** "I believe [specific input/condition] will cause [specific failure] because [reasoning]"
**Vector:** [dimension]
**Severity:** CRITICAL / HIGH / MEDIUM
**Target:** @file:line
**Test sketch:** [2-3 line pseudocode showing the test approach]
**Needs:** [what test infrastructure is required — existing helper, new fixture, docker, etc.]

Report at most 5 attack vectors per dimension. Prioritize by likelihood of finding a real bug.
```

### Dimension 1: Input abuse
Malformed, oversized, empty, null-equivalent, unicode edge cases, type confusion, injection payloads (SQL, OS command, header, path traversal, SSTI/template injection), XSS via stored/reflected input, SSRF through user-controlled URLs, CSRF token bypass, denormalized strings (whitespace-only, zero-width chars, RTL overrides), boundary values (0, -1, max integer, empty string vs null/None).

### Dimension 2: Auth & access control
Token manipulation (expired, future-dated, wrong algorithm, missing claims, extra claims, malformed base64), BOLA/IDOR (accessing resources by manipulating object IDs), BFLA (calling admin/privileged endpoints as regular user), missing authentication on critical functions, privilege escalation (horizontal and vertical), session state attacks (revoked but cached, race between revocation and use), MFA bypass attempts, cookie injection/smuggling.

### Dimension 3: Concurrency & race conditions
TOCTOU between check and use, concurrent mutations to shared state, lock contention under parallel requests, task cancellation mid-operation, cancel-safety violations in async runtimes, channel/queue backpressure, concurrent idempotency key usage, double-spend/duplicate processing from concurrent submissions.

### Dimension 4: Resource exhaustion & limits
Oversized request bodies, header flooding, connection exhaustion, memory pressure from unbounded collections, slow-loris style attacks, rate limit bypass attempts, idempotency store growth without cleanup, ReDoS (catastrophic regex backtracking), decompression bombs (zip/gzip), XXE expansion (billion laughs).

### Dimension 5: State corruption & invariants
Invalid state transitions, partial updates that violate invariants, orphaned records, stale cache entries, insecure deserialization (pickle.loads, yaml.load, jsonpickle — code execution via crafted payloads), deserialization into inconsistent state, strict-mode deserialization bypass, mass assignment (unexpected fields overwriting protected attributes), timestamp manipulation, timezone handling errors.

### Dimension 6: Error handling & dependency resilience
Error message information leakage (stack traces, internal paths, SQL errors, PII/tokens/secrets in logs or responses), error type confusion (wrong status code for error class), unhandled runtime failures (unguarded exceptions, unchecked error returns), silent error swallowing (discarded results, ignored return values). Upstream failure modes: external service timeouts, 5xx responses, partial/malformed responses, retry storms, circuit breaker behavior, outbox consistency under failure, cascading failures from dependency errors, unsafe consumption of upstream APIs (trusting response content without validation).

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

Use `AskUserQuestion` tool: **"N functional test cases + N adversarial vectors. Proceed with test writing, adjust, or stop here (report only)?"**

- **Proceed:** continue to Phase 5.
- **Adjust:** apply the user's changes to the vector list, then re-present.
- **Stop:** skip to Phase 7 (Report) with vectors and hypotheses only — no tests written.

## Phase 5: Write tests

Functional tests first (they establish the baseline), then adversarial. Dispatch test-writing agents sequentially — one per target file (unit tests) or per test file (integration tests).

### Stage 1 agent prompt template (functional)

```
Write functional tests for [target file(s)].

Context:
- Branch: [current branch]
- Test infrastructure: [full explore output from Phase 2 Step 2 — reusable helpers with signatures and import paths, assertion patterns, fixture/factory snippets, supported test types]
- Follow the project's existing test patterns for setup, assertions, and async handling

Test cases (ordered by type):
[For each case: id, title, behavior, type, target, test sketch]

Follow the rules from the Rules section above (Contract: docstrings, naming, helper reuse, production code lock, etc.).

Report:
  WRITTEN: [test count] tests in [file]
  SKIPPED: [count] (not feasible without infrastructure changes)
  BLOCKED: [describe what prevents writing the test]
```

### Stage 2 agent prompt template (adversarial)

Max 8 attack vectors per agent.

```
Write adversarial tests for [target file(s)].

Context:
- Branch: [current branch]
- Test infrastructure: [full explore output from Phase 2 Step 2 — reusable helpers with signatures and import paths, assertion patterns, fixture/factory snippets, supported test types]
- Functional tests already written: [summary of Stage 1 tests — what contracts are locked down]
- Follow the project's existing test patterns for setup, assertions, and async handling

Attack vectors to test (ordered by severity):
[For each vector: id, title, hypothesis, target, test sketch]

Follow the rules from the Rules section above (Hypothesis: docstrings, naming, helper reuse, production code lock, deterministic concurrency tests, etc.). Language rules govern your test scaffolding — adversarial payloads fed into production code under test are unconstrained by them.

After writing each test:
1. State what you expect: PASS (code handles it correctly) or FAIL (test exposes a bug).
2. If you expect FAIL, explain the bug the test would expose.

Report:
  WRITTEN: [test count] tests in [file]
  EXPECTED_PASS: [count] (code is robust)
  EXPECTED_FAIL: [count] (potential bugs found)
  SKIPPED: [count] (not feasible without infrastructure changes)
  BLOCKED: [describe what prevents writing the test — missing fixture, unclear behavior, production code needs changes]
```

**Handle agent status (both stages):**
- **BLOCKED:** Review the blocker. If it requires production code changes or new test infrastructure, record the items as DEFERRED with the reason. Do not stall the workflow.
- **SKIPPED items:** add to the `deferred` list with reason.

After each agent returns:

1. **Type check:**
   Run the project's type checker on the test code (e.g., `uv run mypy` or the equivalent from `/check`).
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
   git add <test_files_only>
   git commit -m "test: [functional|adversarial] tests for [target] — [summary]"
   ```
   Never `git add -A`. Never commit non-test files.

## Phase 6: Verify

Run the full check suite:

```
/check
```

- **All green** → proceed to report.
- **Failures in adversarial tests** → type errors: fix the test. Assertion failures in skip/ignore-annotated tests: expected, verify annotation is correct.
- **Failures in existing tests** → you broke something. Revert the last commit, investigate, rewrite.

## Phase 7: Report

Populate from the `ledger` and `deferred` lists. Each section maps directly to ledger fields.

```markdown
# Test Report

## Scope
[target description, file count, branch]

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

To optimize:  /optimize <feature-slug>
```
