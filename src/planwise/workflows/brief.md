---
description: Plan a task — produces a single task issue
---

# Task Planning Session

Plan a task through three phases: plan, challenge, create the issue.
Do NOT write implementation code — this is planning only.

## What the user wants to work on

$ARGUMENTS

## Phase 0: Resolve input

- **Issue reference** — `$ARGUMENTS` matches an existing issue slug (e.g., `user-auth`, `login-endpoint`).
- **Free text** — anything else.

### If issue reference

```bash
planwise view <slug>
```

Read the issue title and body — treat it as the starting context for Phase 1. You still ask clarifying questions and build the full task body — the issue just replaces a free-text description as the starting point.

### If free text

Proceed directly to Phase 1.

## Phase 1: Plan

Build the task body through conversation — this IS the plan. Focus on the *what* and *why*. Work through each section with the user — use `AskUserQuestion` tool to ask focused questions to fill gaps, don't move on until each section is clear.

### Knowledge base lookup

Before writing the task body, check the knowledge base for relevant domain knowledge.

**Step 1 — Index grep:**

```bash
grep -i "<keywords from user request>" planwise/knowledge/INDEX.md
```

If the index does not exist or the directory is empty, skip to the task body template — there is no prior knowledge.

Match results against domain names, tags, and entry titles. Identify 0-2 relevant domain files and which sections matter. If no domains match, skip to the task body template.

**Step 2 — Domain retrieval:**

Read the matched domain file(s). Either read the full file or retrieve specific sections by offset:
```bash
cat planwise/knowledge/<domain>.md
# or, for targeted retrieval:
grep -n '^## [0-9]' planwise/knowledge/<domain>.md  # section TOC with line numbers
# then read the needed section by offset
```

**Step 3 — Planning-lessons lookup:**

```bash
test -f planwise/knowledge/_lessons.md && grep -i -B1 -A5 "<domain-tag-or-keyword>" planwise/knowledge/_lessons.md
```

Lessons are hypotheses about how to plan better in this codebase, produced by `/memo` Phase 6. Match by `trigger` field (domain tag, file glob, or keyword set). If no file or no match, skip silently. Ignore any hit whose context falls under the `## Archive` heading — those lessons are pruned and not active. For each hit, surface the `lesson` as a planning constraint:
- **risk-miss** lessons → Key Assumptions & Risks (known trap)
- **scope-miss** lessons → Scope (explicit inclusion)
- **approach-wrong** lessons → Technical Context (reject the rejected approach up front)
- **quality-gap** / **estimation-miss** lessons → Key Assumptions & Risks (calibration)

**Contract:** record the retrieved lesson titles as an explicit list. The Pre-creation checklist verifies each one appears in the task body's `## Lessons Applied` section. The usefulness feedback loop in `/memo` Phase 6 depends on this block — retrieving a lesson without emitting the block leaves its usefulness unmeasurable.

Integrate domain knowledge into the task body as you write each section — don't dump it wholesale:
- **5. Constraints** → carry forward into Success Criteria (as guardrails) and Key Assumptions & Risks
- **2. Decisions** → reference in Technical Context. If the new task needs to override a past decision, state explicitly: what the prior decision was, why it no longer holds, and what replaces it
- **4. Gotchas** → carry forward into Key Assumptions & Risks (as known traps)
- **3. Patterns** → reference in Technical Context
- **1. Architecture** → use as the starting mental model for Scope — build on what exists
- **6. Connections** → feed into Phase 2 impact analysis as known ripple effects

**Do NOT:**
- Preload all domain files — most are irrelevant to the current task
- Copy domain file content verbatim into the task body — integrate the specific entries where they inform decisions
- Treat past decisions as immutable — if circumstances changed, override them with explicit justification

### Root cause validation (bugs & fixes only)

If the input describes a problem or bug, ask "Why?" to trace from symptom to root cause before writing the User Story. The User Story should address the root problem, not the surface symptom.

### Task body template

```
## User Story
When [situation], [actor/system] wants to [motivation] so that [expected outcome].

## Success Criteria
How will you know this worked? Measurable outcomes or concrete definition of done.
- Primary: [one metric or observable change with target]
- Guardrail: [what must NOT degrade — omit if not applicable]
(For infrastructure work: "Migration complete, zero downtime, all existing tests pass.")

## Scope
Before writing this section, search the codebase for existing related code — reusable utilities, similar patterns, or partial implementations to build on or avoid duplicating.
What changes, where, how. Not a spec — enough to act on.
Reference existing codebase patterns (CLAUDE.md) where relevant.
Not included: [deliberate exclusions to prevent scope creep]

## Key Assumptions & Risks
What must be true for this approach to work? Known scope traps, technical unknowns, or areas likely to take longer than expected. (bulleted list)

## Technical Context
Architectural decisions, patterns, files affected.

## Lessons Applied
<!-- Include this section only when Step 3 "Planning-lessons lookup" returned hits.
     One line per retrieved lesson, stating the class and exactly where it shaped the spec.
     If no lessons were retrieved, omit the section entirely — do not write "none". -->
- **[Lesson title]** (class) → reflected in *[Section name]* as "<specific sentence or bullet added because of this lesson>"
```

If the Scope reveals a non-trivial architectural choice (e.g., new table vs extend existing, client-side vs server-side), present candidate approaches with trade-offs and ask the user to choose before completing the spec. Skip for straightforward fixes.

### Verify assumptions before presenting

Before presenting to the user, verify every claim in the Technical Context section:
- File paths exist (Glob/ls)
- Function signatures, interface shapes, and schema names match what the code actually has (Read/Grep)
- Referenced CLAUDE.md sections exist and say what you think they say

If any assumption is wrong, correct the task body now — don't carry forward stale information.

Present the completed task body to the user before moving to Phase 2.

## Phase 2: Challenge

Do NOT rationalize skipping steps with: "This is straightforward enough to skip the challenge phase" or "I'll verify this during implementation instead." If a step exists, execute it.

**Pre-mortem:** Imagine the task was implemented and it does not work. What plausible failure scenarios exist? Check if the plan prevents each one.

### Impact analysis

Before stress-testing risks, trace the blast radius.

If knowledge base domain files were loaded in Phase 1, start with their **6. Connections** section — it maps known upstream/downstream dependencies and shared types. Use this as the starting point, then verify and extend with code-level analysis:

For each file in Technical Context:
- Grep for imports/usages of the types, schemas, and interfaces that will change.
- Identify downstream consumers the task doesn't mention — these are hidden dependencies.
- Cross-check against 6. Connections from the knowledge base — are there known ripple effects the code search missed?
- If a downstream file needs updating, add it to the Scope or flag it to the user.

### Risk stress-test

Stress-test the plan against these risks:
- Edge cases not covered?
- Security or data implications?
- Migration or backward compatibility needs? (ask the user)
- Accessibility requirements?
- Dependencies on other tasks or teams?
- Performance implications at scale?
- Observability: what should be logged, monitored, or alerted on?

For each risk found: is it mitigated by the plan, or does the plan need to change?

Then challenge your own output: are any of these risks false positives? Is the plan over-scoped? Is this the simplest approach that solves the problem?

If this reveals genuine technical unknowns, investigate the codebase and report findings to the user before proceeding. Don't commit to a plan that depends on unverified assumptions.

Revise the task body based on findings, or confirm it holds.

Then use `AskUserQuestion` tool to ask: **"Task spec ready. Create the issue, or stop here?"**
- If no -> stop. The task body stays in conversation for later.
- If yes -> proceed to Phase 3.

### Pre-creation checklist

Before creating the issue, verify:
- No placeholder language ("TBD", "add validation", "similar to above", "etc.")
- File paths in Scope verified against current codebase
- Every requirement has a matching success criterion
- **Lessons contract:** if Phase 1 Step 3 returned lesson hits, the task body contains a `## Lessons Applied` section with one line per retrieved lesson (title, class, where it shaped the spec). If Step 3 returned zero hits, the section is absent. A mismatch is a contract violation — fix before creating the issue.

## Phase 3: Create the task issue

**If from issue reference** — upgrade the source issue:

```bash
planwise edit <source-issue-slug> \
  --title "[Task] <keyword title>" \
  --body "<task body from Phase 1>" \
  --label task
planwise status <source-issue-slug> ready
```

**If from free text** — create a new task:

```bash
echo "<task body from Phase 1>" | planwise create task "[Task] <keyword title>"
planwise status <task-slug> ready
```

### Anchor the planning bookmark

Issue-file edits produced by this run need somewhere to land. Anchor a `plan/<task-slug>` bookmark on the highest non-empty change so the epilogue publishes the planning commits:

```bash
PLAN_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
jj bookmark create plan/<task-slug> -r "$PLAN_HEAD" || jj bookmark set plan/<task-slug> -r "$PLAN_HEAD"
```

If the revset returns empty (no file edits — the run upgraded an existing ready issue in-place), skip this step.

### Report

```
Task: <task-slug> — <title>

Scope: [N] files

Next:  /next  (or /next <slug> if multiple tasks were created)
Tip: /clear or /compact first if context is heavy.
```
