---
description: Plan a feature or fix, then create local planning issues
---

# Feature Planning Session

Plan a feature or fix through three phases: plan, challenge, create issues.
Do NOT write implementation code — this is planning only.

**Context discipline:** you are the orchestrator. You hold the user dialogue, the feature body, the sub-feature list, and the pattern bank. Read-heavy blocks are dispatched to subagents that Read their own protocol in `src/planwise/workflows/_plan/` — do NOT Read those files yourself.

## What the user wants to work on

<the user's task>

## Phase 0: Resolve input

- **Issue reference** — `<the user's task>` matches an existing issue slug.
- **Free text** — anything else.

If issue reference: `planwise view <slug>` and use the issue title/body as starting context for Phase 1. If free text: proceed directly to Phase 1.

## Phase 1: Plan

Assemble the feature body through dialogue with the user — User Story, Success Criteria, Scope, Key Assumptions & Risks, Technical Context. One focused round per section; do not move on until the section is clear.

### Root cause validation (bugs & fixes only)

If the input describes a problem or bug, ask "Why?" to trace from symptom to root cause before writing the User Story. The User Story addresses the root problem, not the surface symptom.

### Dispatch — KB retriever (Explore, quick)

> Read `src/planwise/workflows/_plan/analyze.md` § **Knowledge base lookup**. Execute it against keywords: `<user request keywords>`. Return the structured summary the protocol describes.

Integrate the return into the feature body as you draft each section. Carry the Lessons list forward for the Pre-creation checklist.

### Feature body template

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
<!-- Include this section only when the KB retriever returned lesson hits.
     One line per retrieved lesson, stating the class and exactly where it shaped the plan.
     If no lessons were retrieved, omit the section entirely — do not write "none". -->
- **[Lesson title]** (class) → reflected in *[Section name]* as "<specific sentence or bullet added because of this lesson>"

## Sub-Features
<!-- Populated in Phase 3 -->
```

If the Scope reveals a non-trivial architectural choice (e.g., new table vs extend existing, client-side vs server-side), present candidate approaches with trade-offs and ask the user to choose before proceeding to Sub-Features. Skip for straightforward fixes.

### Sub-feature identification

After the feature body is drafted, identify sub-features as **title + one-line scope** each. Slice vertically — each sub-feature delivers a working increment across all needed layers (DB, API, UI), not one layer at a time. Target 1-5 files per sub-feature. If a sub-feature touches more than 5 files, consider splitting. If only 1 trivial change, consider merging. No full bodies yet — those come in Phase 3.

**Sizing check:** each sub-feature should be completable by a subagent in one focused pass (~15-30 min wall clock). If it requires understanding complex interactions across more than 3 distinct subsystems, split it.

For each sub-feature, also determine:
- **Agent approach:** `standard` (read spec → implement → test) or `explore-first` (explore existing patterns before implementing). Use `explore-first` when the sub-feature modifies complex existing code.
- **Dependencies:** which other sub-features must complete before this one can start.

**Parallelism is implicit:** sub-features with the same dependencies and no dependency on each other are naturally parallel — `ready` will return them together.

### Dispatch — Assumption verifier (Explore, quick)

After Technical Context is drafted:

> Read `src/planwise/workflows/_plan/analyze.md` § **Verify assumptions**. Verify these claims: `<file paths, function signatures, schema names, CLAUDE.md references from the draft Technical Context>`. Return corrections.

Apply corrections to the feature body before presenting.

Present the completed feature body + sub-feature list + execution strategy to the user, then proceed to Phase 2.

## Phase 2: Challenge

Dispatch in parallel:

### Dispatch — Impact analyzer (Explore, medium)

> Read `src/planwise/workflows/_plan/challenge.md` § **Impact analysis**. Execute against Technical Context: `<file list, types, schemas, interfaces>`. KB Connections from Phase 1 (if any): `<connections>`. Return the downstream-consumer table.

### Dispatch — Red team (planwise-worker, fresh context)

> Read `src/planwise/workflows/_plan/challenge.md` § **Pre-mortem + Risk stress-test**. Input — feature body + sub-feature list:
> ```
> <paste verbatim>
> ```
> Execute every block. Return failure scenarios, self-challenge, and technical unknowns.

Integrate returns: fold hidden dependencies into existing sub-features or raise to user; revise feature body and sub-features against un-mitigated scenarios. If technical unknowns surface, investigate or raise to the user before committing.

### User gate

Use `AskQuestion` if available (fallback: ask in chat): **"Ready to create issues, or stop here?"**
- If no -> stop. Feature body and sub-feature list stay in conversation for later.
- If yes -> run the Pre-creation checklist, then proceed to Phase 3.

### Pre-creation checklist

Before creating issues, verify:
- Every success criterion in the feature maps to at least one sub-feature
- Every sub-feature traces back to at least one success criterion
- **Lessons contract:** if the KB retriever returned lesson hits, the feature body contains a `## Lessons Applied` section with one line per retrieved lesson (title, class, where it shaped the plan). If zero hits, the section is absent. A mismatch is a contract violation — fix before creating issues.

## Phase 3: Create Issues

### Step 1 — Create the Feature

Use the feature body assembled across Phases 1–2.

**If from issue reference** — upgrade the source issue:

```bash
planwise edit <source-issue-slug> \
  --title "[Feature] <keyword title>" \
  --body "<feature body>" \
  --label feature
planwise status <source-issue-slug> ready
```

**If from free text** — create new:

```bash
echo "<feature body>" | planwise create feature "[Feature] <keyword title>"
planwise status <feature-slug> ready
```

### Step 1.5 — Pattern bank + Buildability

#### Dispatch — Pattern bank (up to 3 Explore agents in parallel)

Assign each agent one slice of the Technical Context. Typical split:
- Agent 1: DB + shared layer
- Agent 2: API layer
- Agent 3: Web layer

Adjust to the feature's actual scope. For small features (1-2 layers), use 1-2 agents.

Each prompt:

> Read `src/planwise/workflows/_plan/create.md` § **Pattern bank extraction**. Your slice: `<slice description + file hints>`. Return findings per the protocol.

Compile the returns into a single **pattern bank** held in main thread. This is the one unavoidable main-thread context cost — downstream subagents consume from it.

**Gate:** do not proceed until the pattern bank is complete. If an agent flags missing files or unexpected structure, resolve with the user first.

#### Dispatch — Buildability reviewer (Explore, quick)

> Read `src/planwise/workflows/_plan/create.md` § **Buildability review**. Pattern bank: `<paste>`. Sub-feature list: `<paste>`. Return per-sub-feature Constraint additions.

Merge returned Constraints into each sub-feature's Constraints block when its body is written in Step 2.

### Step 2 — Create coding sub-features

For each sub-feature, dispatch one subagent:

#### Dispatch — Sub-feature body writer (planwise-worker)

> Read `src/planwise/workflows/_plan/create.md` § **Sub-feature body writer**. Inputs:
> - Sub-feature: `<title, one-line scope, agent approach, dependencies>`
> - Feature slug: `<feature-slug>`
> - Relevant pattern-bank snippets: `<paste subset>`
> - Buildability Constraint addition: `<from buildability returns, or "none">`
>
> Write the body per the template, create the sub-feature via `planwise create sub-feature`, and return the slug, body, and files referenced.

Collect returned slugs and file lists for Step 4.

### Step 3 — Create the UAT sub-feature

One sub-feature for all user testing (main thread — UAT content needs user context):

```bash
echo "<UAT body>" | planwise create uat "[UAT] <feature title> — User Acceptance Testing" --parent <feature-slug> --label user-testing --status ready
```

**UAT body:**

```
## Context
Part of Feature <feature-slug> — [feature title].
Complete AFTER all coding sub-features are done.

## Prerequisites
- Environment: [dev server, staging, local]
- User role: [admin, club member, unauthenticated]
- Test data: [what must exist before testing]

## User Tests
Core:
- [ ] [Test description — what to do and what to expect]
- [ ] [Second core flow]

Edge cases:
- [ ] [Edge case to verify]

Accessibility:
- [ ] [Keyboard navigation works]
- [ ] [Screen reader announces correctly]

Responsive:
- [ ] [Mobile/tablet check if applicable]

## How to Test
[Step-by-step instructions to verify the feature works]

## Done When
All checkboxes checked and the user is satisfied.
```

### Step 4 — Wire dependencies and update the feature

**File conflict check:** compare the `files referenced` lists returned by each body-writer subagent. If two sub-features touch the same file, one must depend on the other — they cannot run in parallel.

For each dependency:

```bash
planwise dep add <sub-feature-id> <depends-on-id>
```

Update the feature body with the Sub-Features section:

```bash
planwise edit <feature-slug> --body "<updated body>"
```

The dependency graph drives execution order — `/implement` uses `ready` to determine what to work on next.

### Step 5 — Anchor the planning bookmark

Issue-file edits produced by this run need somewhere to land. Anchor a `plan/<feature-slug>` bookmark on the highest non-empty change so the epilogue publishes the planning commits:

```bash
PLAN_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
jj bookmark create plan/<feature-slug> -r "$PLAN_HEAD" || jj bookmark set plan/<feature-slug> -r "$PLAN_HEAD"
```

If the revset returns empty (no commits in this run — e.g. the run upgraded an existing ready issue without any file edits), skip this step; the epilogue's conditional push will emit the no-bookmark message.

### Step 6 — Report

```
Feature: <N> — [Feature] <title>

Coding tasks (in order):
  1. <N> — <title> (no dependencies)
  2. <N> — <title> (blocked by <N>)

User testing:
  3. <N> — [UAT] <title>

Next:  /next  (or /next <slug> if multiple issues were created)
Tip: /clear or /compact first if context is heavy.
```
