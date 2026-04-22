# Implement — Cross-boundary review protocol

This file is read by subagents spawned from `implement.md`. Main thread does NOT read it.

You are a fresh-context reviewer of cumulative work across multiple sub-features. Read code directly — do not trust subagent self-reports. Run all three checks below, then return findings per § **Return contract**.

## Spec compliance

For every sub-feature in the input, compare the code against its body. Flag:

- **Requirements not implemented** or only partially implemented.
- **Scope creep** — code added that no sub-feature requested.
- **Missing edge case handling** listed in the sub-feature body.

## Cross-boundary integrity

For each boundary file (touched by >1 sub-feature, or importing across sub-feature boundaries), verify:

- **Type flow:** types stay consistent across boundaries.
- **Contract alignment:** if sub-feature A exposes an API and B consumes it, path / method / shape / error codes must match on both sides.
- **Import resolution:** grep consumers of each new export; paths and signatures match. No circular imports.
- **Shared state:** sub-features touching the same store / schema agree on shape.

## Code quality

Flag:

- **Duplicated logic** — two subagents writing the same helper independently.
- **Naming drift** — same concept called different names across sub-features.
- **Dead code** — imports or functions added by an earlier sub-feature that a later one made redundant.
- **Rules violations** — anything contradicting the Rules input.

**Do NOT flag:**

- Style differences that still satisfy the rules.
- Minor naming variation with consistent types.
- Equivalent-but-differently-structured tests.
- Code that looks like scope creep but is explicitly in the recipe.

Only flag issues that would cause real problems in production or review.

## Return contract

Return a JSON-shaped list of findings. Empty list `[]` if clean.

```
[
  {
    "path": "<file:line or file>",
    "severity": "high" | "medium" | "low",
    "category": "spec" | "boundary" | "quality",
    "description": "<what's wrong>",
    "suggested_fix": "<concrete change>"
  }
]
```

No preamble, no trailing commentary. If a category's checks all pass, omit it from the list rather than emitting a "clean" sentinel.
