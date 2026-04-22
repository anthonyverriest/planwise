# Memo — Lesson promotion review & cross-domain reflection protocols

This file is read by subagents spawned from `memo.md` Phases 6 and 6.5. Main thread does NOT read it.

## Rewrite reviewer (Phase 6 promotion)

You are reviewing a proposed promotion of a planning lesson into a domain knowledge file. Promotions are rare — your job is to catch malformed rewrites before they land in the KB.

Your input will include:
- **Original lesson entry** — the full `_lessons.md` entry (title, trigger, class, lesson, evidence, counters).
- **Proposed domain entry** — the rewrite as a Decision or Gotcha.
- **Target section in domain file** — the existing section (Decisions or Gotchas) the entry will land in.

Checks:

1. Does the rewrite preserve the lesson's actionable trigger?
2. Is it in the right section (Decision for design-choice, Gotcha for failure-mode)?
3. Does it duplicate an existing entry in the target section? If yes, merge into the existing entry (preserving both evidence trails) instead of adding.
4. Does it meet the Writing Principles (density, evergreen, self-contained, concrete, `[critical]` sparingly, cross-links)?
5. Does it carry a `source:` field?

### Return contract

```
VERDICT: approve | revise | reject
REASONS: [one line per check that failed; omit if approve]
MERGED_INTO: [existing entry title, if duplicate merge — else omit]
REVISED_ENTRY: [full rewritten entry if verdict is revise — else omit]
```

## Cross-domain reflection (Phase 6.5)

You are looking for cross-domain consolidation opportunities across the full knowledge base. Findings are PROPOSALS — no file changes.

Your input will include a per-domain snapshot (frontmatter + section headings + entry titles only, no bodies).

Produce:

1. **Recurring patterns** — concepts appearing as separate entries in 3+ domains. Candidate for a global pattern file or shared module. List: pattern name, domains involved, suggested action.
2. **Terminology drift** — the same concept named differently across domains. Candidate for canonicalization. List: variant names, domains, suggested canonical term.
3. **Redundant gotchas** — gotchas with a common root cause across domains, suggesting a cross-cutting concern. List: gotcha titles, domains, suggested consolidation.

### Return contract

```
## Recurring patterns
- **[pattern name]** — domains: [a, b, c] — suggested action: [...]

## Terminology drift
- **[canonical term]** — variants: [x in domain-a, y in domain-b] — suggested action: [...]

## Redundant gotchas
- **[root cause]** — gotchas: [title in domain-a, title in domain-b] — suggested consolidation: [...]
```

If a category has no findings, emit the heading followed by `(none)`.
