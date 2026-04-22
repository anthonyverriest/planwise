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
- **Commit the failing test on its own change** so `/implement` picks up a clean starting point, not a polluted working copy. The bug slug is not yet known (Phase 4 creates it); commit with a symptom placeholder and capture the change-id — Phase 4 will rewrite the description with the real slug:
  ```bash
  jj commit <test-file> -m "test: failing repro for <symptom>"
  FAILING_TEST_CHANGE=$(jj log -r @- --no-graph -T 'change_id.short()')
  ```
  Record `$FAILING_TEST_CHANGE` — you need it in Phase 4.

If a failing test is genuinely impractical (e.g., visual layout glitch and no visual harness), say so explicitly in the body and explain why. Do not silently skip.

### If regression

Primary forensic: annotate the suspect file to see which change last modified each line (jj's equivalent of `git blame`):

```bash
jj file annotate <suspect-file>
```

Focus on the line(s) matching the bug symptom — the annotation maps each line directly to the change-id that introduced it.

For broader context, walk the chronological change history that touched the file:

```bash
jj log -r 'file("<suspect-file>")' --limit 20 -T builtin_log_oneline
```

If a specific change-id looks suspect, inspect its full evolution (rewrites, amends, prior states before the current snapshot) — this is jj-only signal that often reveals why the bad line landed:

```bash
jj evolog <suspect-change-id>
```

If the window is bigger than ~10 changes, manual-bisect to narrow. Record `<change-id> <description>` for the body.

## Phase 2: Diagnose & spec

### Knowledge base lookup

```bash
grep -i "<keywords from symptom>" planwise/knowledge/INDEX.md
```

If no index or no match, skip. Otherwise read 0–2 matched domain files and weight integration toward:
- **4. Gotchas** → carry into *Constraints* / *Regression surface*
- **2. Decisions** → carry into *Constraints* (override only with explicit justification)
- **6. Connections** → reserve for Phase 3 impact analysis

### Planning-lessons lookup

```bash
test -f planwise/knowledge/_lessons.md && grep -i -B1 -A5 "<symptom-keywords-or-affected-file-glob>" planwise/knowledge/_lessons.md
```

Lessons are hypotheses about how to plan better in this codebase, produced by `/memo` Phase 6. Match by `trigger` field (domain tag, file glob drawn from affected files, or keyword set from the symptom). If no file or no match, skip silently. Ignore any hit whose context falls under the `## Archive` heading — those lessons are pruned and not active. For each hit, shape diagnosis:
- **risk-miss** lessons → treat the named assumption as a high-probability root cause candidate; check it early before exploring other hypotheses
- **approach-wrong** lessons → if the bug trace points at a previously-rejected approach, the root cause may be that the approach is re-emerging; widen suspects to include anything that reintroduced it
- **scope-miss** / **estimation-miss** / **quality-gap** lessons → usually irrelevant at diagnosis time; skip unless the lesson directly names a concrete failure mode

**Contract:** record the retrieved lesson titles as an explicit list. The Pre-creation checklist verifies each one appears in the bug body's `## Lessons Applied` section. `/memo` Phase 6 Step 1.5 reads this block from bug sub-feature bodies (alongside feature bodies) to score whether the lesson prevented its claimed defect class — retrieving a lesson without emitting the block leaves its usefulness unmeasurable.

Bug never writes to `_lessons.md` — single-bug diagnosis is single-signal and won't converge; production is reserved for `/memo` at the feature level.

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
- Regressed by: <change-id short-description>   (omit if not a regression or not isolated)

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

## Lessons Applied
<!-- Include this section only when the Planning-lessons lookup returned hits.
     One line per retrieved lesson, stating the class and exactly where it shaped the diagnosis or fix.
     If no lessons were retrieved, omit the section entirely — do not write "none". -->
- **[Lesson title]** (class) → reflected in *[Section name]* as "<specific sentence or bullet added because of this lesson>"
```

### Verify assumptions before presenting

- File paths in *Root Cause* and *Implementation Notes* exist (Glob/Read)
- Function signatures, schemas, and interfaces match what the code actually has (Read/Grep)
- Referenced CLAUDE.md sections exist and say what you think they say
- The `Regressed by` change (if present) actually touches the cited lines (`jj show <change-id> <file>`)
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
- **Lessons contract:** if the Planning-lessons lookup returned hits, the bug body contains a `## Lessons Applied` section with one line per retrieved lesson (title, class, where it shaped the diagnosis or fix). If the lookup returned zero hits, the section is absent. A mismatch is a contract violation — fix before creating the issue.

## Phase 4: Create the bug issue

**If parented:**

```bash
echo "<bug body from Phase 2>" | planwise create bug "Fix: <concise description>" --parent <parent-slug>
```

**If standalone:**

```bash
echo "<bug body from Phase 2>" | planwise create bug "Fix: <concise description>"
```

Capture the new slug from the create output (e.g. `B42-theme-toggle-persists`). Rewrite the failing-test commit description so its `(#<slug>)` suffix matches the convention used by `/memo` and other history-mining workflows:

```bash
jj describe "$FAILING_TEST_CHANGE" -m "test: failing repro for <symptom> (#<new-slug>)"
```

Promote to ready so `/implement` will pick it up:

```bash
planwise status <new-slug> ready
```

### Anchor the bug bookmark

The failing-test commit and the bug issue file need somewhere to land. Anchor a `bug/<new-slug>` bookmark on the highest non-empty change so the epilogue publishes them:

```bash
BUG_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
jj bookmark create bug/<new-slug> -r "$BUG_HEAD" || jj bookmark set bug/<new-slug> -r "$BUG_HEAD"
```

### Report

```
Bug: <new-slug> — Fix: <description>
Triage: <severity> / <priority> / <reproducibility>
[If parented:  Linked to <parent-type> <parent-slug>]
[If standalone: Standalone bug — no parent]
[If regression: Regressed by <change-id>]
Failing test: @<test-path>
Status: ready

Next:  /next  (or /next <slug> if multiple bugs were created)
Tip: /clear or /compact first if context is heavy.
```
