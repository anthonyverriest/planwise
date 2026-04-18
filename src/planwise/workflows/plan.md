---
description: Plan a feature or fix, then create local planning issues
---

# Feature Planning Session

Plan a feature or fix through three phases: plan, challenge, create issues.
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

Read the issue title and body — treat it as the starting context for Phase 1. You still ask clarifying questions and build the full feature body — the issue just replaces a free-text description as the starting point.

### If free text

Proceed directly to Phase 1.

## Phase 1: Plan

Build the feature body through conversation — this IS the plan. Focus on the *what* and *why* — leave the *how* to sub-features. Work through each section with the user — use `AskUserQuestion` tool to ask focused questions to fill gaps, don't move on until each section is clear.

### Knowledge base lookup

Before writing the feature body, check the knowledge base for relevant domain knowledge.

**Step 1 — Index grep:**

```bash
grep -i "<keywords from user request>" planwise/knowledge/INDEX.md
```

If the index does not exist or the directory is empty, skip to the feature body template — there is no prior knowledge.

Match results against domain names, tags, and entry titles. Identify 0-2 relevant domain files and which sections matter. If no domains match, skip to the feature body template.

**Step 2 — Domain retrieval:**

Read the matched domain file(s). Either read the full file or retrieve specific sections by offset:
```bash
cat planwise/knowledge/<domain>.md
# or, for targeted retrieval:
grep -n '^## [0-9]' planwise/knowledge/<domain>.md  # section TOC with line numbers
# then read the needed section by offset
```

Integrate domain knowledge into the feature body as you write each section — don't dump it wholesale:
- **5. Constraints** → carry forward into Success Criteria (as guardrails) and Key Assumptions & Risks
- **2. Decisions** → reference in Technical Context. If the new feature needs to override a past decision, state explicitly: what the prior decision was, why it no longer holds, and what replaces it
- **4. Gotchas** → carry forward into Key Assumptions & Risks (as known traps)
- **3. Patterns** → reference in Technical Context and carry forward to Phase 3 pattern bank
- **1. Architecture** → use as the starting mental model for Scope — build on what exists
- **6. Connections** → feed into Phase 2 impact analysis as known ripple effects

**Do NOT:**
- Preload all domain files — most are irrelevant to the current feature
- Copy domain file content verbatim into the feature body — integrate the specific entries where they inform decisions
- Treat past decisions as immutable — if circumstances changed, override them with explicit justification

### Root cause validation (bugs & fixes only)

If the input describes a problem or bug, ask "Why?" to trace from symptom to root cause before writing the User Story. The User Story should address the root problem, not the surface symptom.

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

## Sub-Features
<!-- Populated in Phase 3 -->
```


If the Scope reveals a non-trivial architectural choice (e.g., new table vs extend existing, client-side vs server-side), present candidate approaches with trade-offs and ask the user to choose before proceeding to Sub-Features. Skip for straightforward fixes.

After completing the feature body, identify sub-features as **title + one-line scope** each. Slice vertically — each sub-feature should deliver a working increment across all needed layers (DB, API, UI), not one layer at a time. Target 1-5 files per sub-feature. If a sub-feature touches more than 5 files, consider splitting. If it touches only 1 trivial change, consider merging with a related sub-feature. No full bodies yet — those come in Phase 3 after the challenge.

**Sizing check:** each sub-feature should be completable by a subagent in one focused pass (~15-30 min wall clock). If a sub-feature requires understanding complex interactions across more than 3 distinct subsystems, it's too large — split it.

For each sub-feature, also determine:
- **Agent approach:** `standard` (read spec -> implement -> test) or `explore-first` (explore existing patterns in related code before implementing). Use `explore-first` when the sub-feature modifies complex existing code that the agent needs to understand first.
- **Dependencies:** which other sub-features must complete before this one can start. These are wired via `dep add` in Phase 3.

**Parallelism is implicit:** sub-features with the same dependencies and no dependency on each other are naturally parallel — `ready` will return them together.

### Verify assumptions before presenting

Before presenting to the user, verify every claim in the Technical Context section:
- File paths exist (Glob/ls)
- Function signatures, interface shapes, and schema names match what the code actually has (Read/Grep)
- Referenced CLAUDE.md sections exist and say what you think they say

If any assumption is wrong, correct the feature body now — don't carry forward stale information.

Present the completed feature body, sub-feature list, and execution strategy to the user before moving to Phase 2.

## Phase 2: Challenge

Do NOT rationalize skipping steps with: "This is straightforward enough to skip the challenge phase", "The sub-features are clear enough without the pattern bank", or "I'll verify this during implementation instead." If a step exists, execute it.

**Pre-mortem:** Imagine the feature was implemented and the feature does not work. What plausible failure scenarios exist? Check if the plan prevents each one.

### Impact analysis

Before stress-testing risks, trace the blast radius.

If knowledge base domain files were loaded in Phase 1, start with their **6. Connections** section — it maps known upstream/downstream dependencies and shared types. Use this as the starting point, then verify and extend with code-level analysis:

For each file in Technical Context:
- Grep for imports/usages of the types, schemas, and interfaces that will change.
- Identify downstream consumers the feature doesn't mention — these are hidden dependencies.
- Cross-check against 6. Connections from the knowledge base — are there known ripple effects the code search missed?
- If a downstream file needs updating, either add it to an existing sub-feature or flag it to the user.

### Risk stress-test

Stress-test the plan against these risks:
- Edge cases not covered?
- Security or data implications?
- Migration or backward compatibility needs? (ask the user)
- Accessibility requirements?
- Dependencies on other features or teams?
- Performance implications at scale?
- Observability: what should be logged, monitored, or alerted on?

For each risk found: is it mitigated by the plan, or does the plan need to change?

Then challenge your own output: are any of these risks false positives? Is the plan over-scoped? Is this the simplest approach that solves the problem?

If this reveals genuine technical unknowns, investigate the codebase and report findings to the user before proceeding. Don't commit to a plan that depends on unverified assumptions.

Revise the feature body and sub-feature list based on findings, or confirm they hold.

Then use `AskUserQuestion` tool to ask: **"Ready to create issues, or stop here?"**
- If no -> stop. The feature body and sub-feature list stay in conversation for later.
- If yes -> proceed to Phase 3.

### Pre-creation checklist

Before creating issues, verify:
- Every success criterion in the feature maps to at least one sub-feature
- Every sub-feature traces back to at least one success criterion

## Phase 3: Create Issues

Push the feature body from Phase 1 and elaborate sub-features into full local planning issues.

### Step 1: Create the Feature

Use the feature body built in Phase 1 (with any Phase 2 revisions).

**If from issue reference** — upgrade the source issue into the feature and promote to ready:

```bash
planwise edit <source-issue-slug> \
  --title "[Feature] <keyword title>" \
  --body "<feature body from Phase 1>" \
  --label feature
planwise status <source-issue-slug> ready
```

**If from free text** — create a new issue directly at ready:

```bash
echo "<feature body from Phase 1>" | planwise create feature "[Feature] <keyword title>"
planwise status <feature-slug> ready
```

### Step 1.5: Extract implementation patterns (pattern bank)

Before writing any sub-feature bodies, gather all code patterns the recipes will reference. This is the brain's deep read of the codebase — front-load it here so recipe writing becomes mechanical assembly.

**Launch up to 3 Explore agents in parallel**, each focused on a different area of the feature's Technical Context:

```
Agent 1: DB + shared layer — read table definitions, schemas, shared types
Agent 2: API layer — read route files, service files, interfaces, existing validation patterns
Agent 3: Web layer — read form components, type files, schema files, detail/list pages
```

Adjust agent focus based on the feature's actual scope. For small features (1-2 layers), use 1-2 agents.

Each agent should report:
- **Current imports** and their sources for each file
- **Exact code snippets** showing existing patterns new code should follow (copy-paste, not paraphrase)
- **Function signatures, interface shapes, schema definitions** the recipes will reference
- **Insertion points** — the target location (function name, block, or surrounding context) where new code should go
- **Downstream consumers** — files that import the types/schemas being modified (confirms impact analysis from Phase 2)

Compile the agent findings into a **pattern bank** — a working set of code snippets organized by file. This pattern bank is the source material for all Implementation Recipe steps. Every "Pattern to follow" snippet in a recipe MUST come from this bank.

**Gate:** Do NOT proceed to Step 2 until the pattern bank is complete. If an agent reports missing files or unexpected code structure, resolve with the user before writing recipes.

**Buildability check (devil's advocate):** Now that the pattern bank reveals actual code structure, stress-test each sub-feature: what could the implementing agent misinterpret, over-engineer, or get wrong? Tighten the sub-feature scope or add Constraints to prevent it. This check was deferred from Phase 2 because it requires code-level understanding to be useful.

### Step 2: Create coding sub-features

Elaborate each sub-feature identified in Phase 1 into a full issue body. For each:

```bash
echo "<sub-feature body>" | planwise create sub-feature "<keyword title>" --parent <feature-slug> --agent <standard|explore-first> --status ready
```

The `--parent` flag automatically links the sub-feature to the feature.

For each sub-feature, before writing the body:
1. Pull relevant snippets from the **pattern bank** (Step 1.5) — these become the pattern snippets in the recipe. Do not re-read files; the pattern bank is the source of truth for planning consistency.
2. Write Requirements as testable assertions, not descriptions.
3. Write the commit message format and scope: `<type>: <description> (#<sub-feature-slug>)`. The implementer writes the final message based on what was actually done.
4. Write the exact validation command to run after.

**Every coding sub-feature body MUST include ALL sections:**

```
## Context
Part of Feature <feature-slug> — [feature title].
[Why this sub-feature exists. What comes before it. What depends on it.]

## Requirements
1. [First precise, testable requirement]
2. [Second requirement]
3. [Continue — each must be unambiguous and verifiable]

## Edge Cases & Error Handling
- [Empty state: what happens when there's no data?]
- [Boundary: max/min values, long strings, special characters]
- [Error scenario: network failure, invalid input, concurrent edits]
- [Permission: unauthorized access attempt]

## Constraints
[What MUST NOT change. Existing behavior to preserve.]
- MUST NOT break: [specific existing behavior]
- MUST NOT change: [specific API contract, schema, or UI behavior]
(Use "None" if this sub-feature has no regression-sensitive boundaries.)

## Implementation Recipe

Where to change, what patterns to follow, and what needs to happen.
The implementing agent writes the code — these notes provide direction, not dictation.
MUST NOT contain placeholder language — every instruction must be actionable as written.

### Files & Patterns
For each file to modify, include:
- Exact path (`src/package/path/to/file.py`)
- What to change (which functions, interfaces, schemas, or blocks)
- Pattern to follow — paste a code snippet from the pattern bank showing the existing shape to replicate. The implementer will read the file before editing and should trust the current code over a stale snippet if they diverge.

### Validation
[Exact command to run — e.g., `uv run pytest`, `uv run mypy src/`]

### Commit
[Format: `<type>: <description> (#<sub-feature-slug>)` — the implementer writes the final message based on what was actually done, using this type and scope as guidance]

## Acceptance Criteria
[One concrete, testable criterion per Requirement and Edge Case. No meta-criteria like "All requirements verified".]
- [ ] [Specific observable outcome]
- [ ] [Continue — each must be verifiable on its own]
- [ ] Tests written and passing for all criteria above (if applicable)

## Dependencies
[Blocked by <XX> or "None"]
```

**Post-elaboration checklist** — verify across all sub-feature bodies before proceeding:
- No placeholder language ("TBD", "add validation", "similar to above", "etc.")
- Type names, schema names, and route paths are consistent across all sub-features
- Every file path in Implementation Recipe exists in the current codebase (verify with Glob/ls)
- Every "Pattern to follow" snippet is grounded in actual code from the pattern bank (not invented or paraphrased from memory)
- Every recipe step has a concrete location (function name, block name, or surrounding context)
- Validation command is a real command that exists in the project
- **Type flow check:** trace the data type across sub-feature boundaries. Verify they align across layers.
- **No orphaned consumers:** every downstream file identified in the impact analysis is covered by a recipe step

### Step 3: Create the UAT sub-feature

One sub-feature for all user testing:

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

### Step 4: Wire dependencies and update the feature

For each sub-feature that depends on another, wire the dependency:

```bash
planwise dep add <sub-feature-id> <depends-on-id>
```

**File conflict check:** Before wiring, compare Implementation Recipe file lists across sub-features. If two sub-features touch the same file, one must depend on the other — they cannot run in parallel.

Then update the feature body with the Sub-Features section:

```bash
planwise edit <feature-slug> --body "<updated body>"
```

The Sub-Features section lists all sub-features. The dependency graph (via `dep add`) drives execution order — `/implement` uses `ready` to determine what to work on next.

### Step 5: Report

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
