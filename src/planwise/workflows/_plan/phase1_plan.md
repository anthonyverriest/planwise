# Phase 1 — Dispatchable protocols

This file is read by subagents spawned from `plan.md`. Main thread does NOT read it.

## Knowledge base lookup

Before the orchestrator writes the feature body, check the knowledge base for relevant domain knowledge.

**Step 1 — Index grep:**

```bash
grep -i "<keywords from user request>" planwise/knowledge/INDEX.md
```

If the index does not exist or the directory is empty, return "no prior knowledge" — there is nothing to integrate.

Match results against domain names, tags, and entry titles. Identify 0-2 relevant domain files and which sections matter. If no domains match, return "no prior knowledge."

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

**Contract:** record the retrieved lesson titles as an explicit list. The orchestrator's Pre-creation checklist verifies each one appears in the feature body's `## Lessons Applied` section. The usefulness feedback loop in `/memo` Phase 6 depends on this block — retrieving a lesson without emitting the block leaves its usefulness unmeasurable.

### Integration guidance to return

Tell the orchestrator how each retrieved entry maps to the feature body:
- **5. Constraints** → Success Criteria (as guardrails) and Key Assumptions & Risks
- **2. Decisions** → Technical Context. If the new feature needs to override a past decision, state: what the prior decision was, why it no longer holds, and what replaces it
- **4. Gotchas** → Key Assumptions & Risks (as known traps)
- **3. Patterns** → Technical Context and Phase 3 pattern bank
- **1. Architecture** → starting mental model for Scope — build on what exists
- **6. Connections** → Phase 2 impact analysis as known ripple effects

### Return shape

Return a single structured summary:
- Matched domains (name + one-line why relevant); empty list if none
- Per-section integration entries: `{target feature-body section, exact sentence or bullet to add, source domain + entry}`
- Lessons list: `{title, class, target section, exact sentence to add}`

**Do NOT:**
- Preload all domain files — most are irrelevant to the current feature
- Copy domain file content verbatim — integrate the specific entries where they inform decisions
- Treat past decisions as immutable — if circumstances changed, override with explicit justification

## Verify assumptions

Verify every claim the orchestrator makes in the feature body's Technical Context section:
- File paths exist (Glob/ls)
- Function signatures, interface shapes, and schema names match what the code actually has (Read/Grep)
- Referenced CLAUDE.md sections exist and say what the Technical Context claims

### Return shape

For each claim that is wrong, return `{claim as stated, what the code actually shows, suggested correction}`. If all claims hold, return "all claims verified."
