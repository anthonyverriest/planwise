# Phase 3 — Dispatchable protocols

This file is read by subagents spawned from `plan.md`. Main thread does NOT read it.

## Pattern bank extraction

Gather all code patterns the sub-feature recipes will reference. Front-load the codebase deep-read here so recipe writing becomes mechanical assembly.

Each pattern-bank subagent is assigned one slice of the Technical Context (e.g. DB + shared layer, API layer, Web layer). Adjust scope to the slice the orchestrator passes.

Each agent reports:
- **Current imports** and their sources for each file
- **Exact code snippets** showing existing patterns new code should follow (copy-paste, not paraphrase)
- **Function signatures, interface shapes, schema definitions** the recipes will reference
- **Insertion points** — the target location (function name, block, or surrounding context) where new code should go
- **Downstream consumers** — files that import the types/schemas being modified (confirms impact analysis from Phase 2)

### Return shape

Return findings grouped by file: `{file path, imports, snippets, signatures, insertion points, downstream consumers}`. The orchestrator compiles all returns into a single pattern bank held in main thread — downstream subagents (buildability reviewer, sub-feature body writer) consume from it.

If the slice reveals missing files or unexpected code structure, flag it explicitly — the orchestrator resolves with the user before writing recipes.

## Buildability review

Now that the pattern bank reveals actual code structure, stress-test each sub-feature: what could the implementing agent misinterpret, over-engineer, or get wrong? This check requires code-level understanding — that's why it runs after the pattern bank, not during Phase 2.

Inputs from the orchestrator:
- Pattern bank (compiled from the extraction step above)
- Sub-feature list (title + one-line scope + agent approach)

### Return shape

Per sub-feature, return: `{sub-feature title, risk, concrete Constraint line to add to the sub-feature's Constraints block}`. If a sub-feature has no identifiable risk, return "no addition needed" for it.

## Sub-feature body writer

Write one full sub-feature issue body and create the issue.

Inputs from the orchestrator:
- Sub-feature: title, one-line scope, agent approach (`standard` or `explore-first`), dependencies
- Feature slug (for `--parent` and the Context section)
- Relevant pattern-bank snippets (the subset this sub-feature needs)
- Buildability Constraint addition (if any)

### Body template — every section MUST be present

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
- Pattern to follow — paste a code snippet from the pattern bank showing the existing shape to replicate.

### Validation
[Exact command to run — e.g., `uv run pytest`, `uv run mypy src/`]

### Commit
[Format: `<type>: <description> (#<sub-feature-slug>)`]

## Acceptance Criteria
[One concrete, testable criterion per Requirement and Edge Case. No meta-criteria like "All requirements verified".]
- [ ] [Specific observable outcome]
- [ ] [Continue — each must be verifiable on its own]
- [ ] Tests written and passing for all criteria above (if applicable)

## Dependencies
[Blocked by <XX> or "None"]
```

### Writing rules

1. Pull pattern snippets ONLY from the pattern bank the orchestrator passed. Do not re-read files — the pattern bank is the source of truth.
2. Write Requirements as testable assertions, not descriptions.
3. Merge the buildability Constraint (if provided) into the Constraints block.
4. No placeholder language ("TBD", "add validation", "similar to above", "etc.").
5. Every file path in Files & Patterns must exist — trust the pattern bank; if a path isn't covered there, flag it to the orchestrator rather than invent one.
6. Every recipe step must have a concrete location (function name, block, or surrounding context).

### Create the issue

After writing the body, create the sub-feature:

```bash
echo "<body>" | planwise create sub-feature "<title>" --parent <feature-slug> --agent <standard|explore-first> --status ready
```

### Return shape

Return: `{sub-feature slug, final body, files referenced in Files & Patterns}`. The orchestrator uses `files referenced` for the file-conflict check in Step 4.
