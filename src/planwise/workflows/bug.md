---
description: Diagnose a bug — triage, reproduce, root cause, then create the issue
---

# Bug Diagnosis Session

Diagnose a bug through four phases: **triage & reproduce → diagnose → challenge → create**.
You DO write the failing test that captures the bug. You do NOT write the fix — that is `/implement`.

## What the user reported

$ARGUMENTS

## Phase 0: Resolve input

- **Parented bug** — first whitespace-delimited token resolves to an existing issue slug (`planwise view <token>` succeeds). Remainder is the bug description. The resolved issue is the parent (feature, sub-feature, or task — all valid).
- **Standalone bug** — first token is not a known slug. Whole `$ARGUMENTS` is the description. No parent.
- **Ambiguous** — slug-shaped but not found. Use `AskUserQuestion`: typo, or free text starting with a slug-like word?

```bash
planwise view <parent-slug>                 # parented path
planwise list --children-of <parent-slug>   # only if parent is a feature
```

## Phase 1: Triage & reproduce

### Triage

Capture four fields. Infer from the report; ask only for what you can't.

- **Severity** — `S1` data loss/crash/security · `S2` major broken, no workaround · `S3` partial, workaround exists · `S4` cosmetic
- **Priority** — `P0` fix now · `P1` this iteration · `P2` soon · `P3` backlog
- **Reproducibility** — `always` · `intermittent` (note rate if known) · `once` · `cannot`
- **Regression?** — `yes` (worked before) · `no` (never worked) · `unknown`

### Quick duplicate check

```bash
planwise list --type bug
```

Grep titles for the symptom keyword. If a candidate matches, `planwise view` it and ask the user: same, related, or distinct? If duplicate → stop, point them at the existing slug.

### Reproduce

Execute the user's steps. CLI → run it. API → hit the endpoint. UI → walk the flow in the dev server. Library → smallest script that exercises the API.

- If it reproduces → record the exact observed output (error, wrong value).
- If it does NOT reproduce after 3 attempts → mark `reproducibility: cannot`, ask the user for missing setup/env/role, and do not proceed until you can reproduce or jointly confirm it's environment-specific.

### Minimize and capture

Strip the steps to the smallest set that still triggers the bug. Then write a failing test:

- Place it where existing tests live (match `CLAUDE.md` conventions).
- Name it after the symptom (e.g., `test_theme_toggle_persists_across_refresh`).
- Run it; confirm it fails with the same symptom.
- Record the path — it goes in the body.

If a failing test is genuinely impractical (e.g., visual layout glitch and no visual harness), say so explicitly in the body and explain why. Do not silently skip.

### If regression

```bash
git log --oneline -20 -- <suspect-file>
```

Identify the suspect commit. If the window is bigger than ~10 commits, manual-bisect to narrow. Record `<hash> <subject>` for the body.

## Phase 2: Diagnose & spec

### Knowledge base lookup

```bash
grep -i "<keywords from symptom>" planwise/knowledge/INDEX.md
```

If no index or no match, skip. Otherwise read 0–2 matched domain files and weight integration toward:
- **4. Gotchas** → carry into *Constraints* / *Regression surface*
- **2. Decisions** → carry into *Constraints* (override only with explicit justification)
- **6. Connections** → reserve for Phase 3 impact analysis

### Root cause

You have the failing test from Phase 1 — that's the proximate symptom. Trace from there to root cause by asking *Why?* until the answer is actionable (a specific code, config, schema, or spec change fixes it). Cite each layer with `@package/path:line`.

If the analysis surfaces a non-trivial fix choice (patch at call site vs fix shared utility, narrow vs broad), present candidates with trade-offs and let the user choose before writing the body.

### Bug body template

```
## Triage
- Severity: <S1|S2|S3|S4>
- Priority: <P0|P1|P2|P3>
- Reproducibility: <always|intermittent (rate)|once|cannot>
- Regression: <yes|no|unknown>
- Regressed by: <commit-hash short-subject>   (omit if not a regression or not isolated)

## Context
[If parented: "Part of <parent-type> <parent-slug> — [parent title]." Add UAT linkage if found during user acceptance testing.]
[If standalone: "Found out of scope while [activity]. Affects <area>." No parent.]

## Symptom
**What happens:** [observed behavior — quote the actual error/output]
**What should happen:** [expected correct behavior]
**Minimized repro:**
1. [Smallest step]
2. [...]
[Optional: pre-conditions / environment if they materially matter — auth state, flag, browser, runtime]

## Failing Test
- Path: `@<test-file>:<line>` (or `@<test-file>` if new)
- Currently fails with: [exact assertion / error]
- (Or: explain why a test isn't practical and what manual check replaces it.)

## Root Cause
[Result of the Why? chain — state the root in one sentence, then list the chain.
Cite suspect files with `@package/path:line` at each layer.]

## Requirements
1. [Precise fix requirement — each must be testable]
2. [Continue as needed]

## Constraints
- MUST NOT break: [existing behavior to preserve]
- MUST NOT change: [API contract, schema, UI behavior]
(Use "None" if no regression-sensitive boundaries.)

## Implementation Notes
[Suggested approach. Reference CLAUDE.md where relevant.
MUST include exact file paths to investigate or modify (use `@package/path:line`).
MUST NOT contain placeholder language — every instruction must be actionable as written.]

## Verification
- **Target:** failing test above passes.
- **Regression matrix:** [list each at-risk scenario with a concrete check — command, URL, or test name]

## Acceptance Criteria
- [ ] Failing test passes
- [ ] All requirements verified
- [ ] Regression matrix items verified unchanged
- [ ] No new test failures introduced

## Dependencies
[Blocked by <slug> or "None"]
```

### Verify assumptions before presenting

- File paths in *Root Cause* and *Implementation Notes* exist (Glob/Read)
- Function signatures, schemas, and interfaces match what the code actually has (Read/Grep)
- Referenced CLAUDE.md sections exist and say what you think they say
- The `Regressed by` commit (if present) actually touches the cited lines (`git show <hash> -- <file>`)
- The failing test was actually run and actually fails

If anything is wrong, correct the body now.

Present the completed bug body to the user before Phase 3.

## Phase 3: Challenge

Do NOT rationalize skipping steps. If a step exists, execute it.

**Pre-mortem:** Imagine the fix shipped, and either (a) the bug returned, or (b) a new bug appeared as a result of the fix. What scenarios produce each? Does the body prevent them?

### Regression impact analysis

If KB domains were loaded, start with their **6. Connections** section, then verify and extend with code-level analysis:

- Grep for callers/consumers of the function, component, type, or schema being changed.
- Identify other features that exercise the same code path — they are at regression risk.
- For each affected downstream: is it covered by *Constraints* and the *Verification* regression matrix? If not, expand them.

### Risk stress-test

- Will the fix introduce a new edge case the bug masked?
- Security implications of the bug *or* the fix?
- Data integrity — corrupted data already in the wild? Backfill needed? (For `S1` data bugs, ask the user explicitly.)
- Backward compatibility — observable behavior change?
- Observability — should the fix add a log/metric so a regression is detectable in prod?

For each risk: mitigated, or revise the body?

Then challenge your own output: false positives? Over-scoped? Simplest change that addresses the root cause?

If unknowns remain, investigate before proceeding. Don't commit to a plan that depends on unverified assumptions.

Then use `AskUserQuestion`: **"Bug spec ready. Create the issue, or stop here?"**
- No → stop. Body and failing test stay in conversation.
- Yes → Phase 4.

### Pre-creation checklist

- No placeholder language ("TBD", "fix the thing", "etc.")
- File paths in *Root Cause* and *Implementation Notes* verified against current codebase
- Failing test exists and was run (or its absence is explicitly justified)
- Every requirement has a matching acceptance criterion
- *Verification* regression matrix has a concrete check per item
- Repro steps are minimized

## Phase 4: Create the bug issue

**If parented:**

```bash
echo "<bug body from Phase 2>" | planwise create bug "Fix: <concise description>" --parent <parent-slug>
```

**If standalone:**

```bash
echo "<bug body from Phase 2>" | planwise create bug "Fix: <concise description>"
```

Promote to ready so `/implement` will pick it up:

```bash
planwise status <new-slug> ready
```

### Report

```
Bug: <new-slug> — Fix: <description>
Triage: <severity> / <priority> / <reproducibility>
[If parented:  Linked to <parent-type> <parent-slug>]
[If standalone: Standalone bug — no parent]
[If regression: Regressed by <commit-hash>]
Failing test: @<test-path>
Status: ready

Next:  /next  (or /next <slug> if multiple bugs were created)
```
