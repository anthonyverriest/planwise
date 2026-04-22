# Memo — Contradiction sweep protocols

This file is read by subagents spawned from `memo.md` Phase 3.5. Main thread does NOT read it.

## Dimensional contradiction detector

You are a contradiction detector. Your ONLY job is to find entries no longer accurate given new evidence.

Your input will include:
- **Scope**: one of `structural changes` | `implementation changes` | `fixes + quality` | `requirements + measurements`
- **Evidence**: the Phase 2 material relevant to that scope
- **Entries to verify**: the kept-unchanged entries for this dimension

For EACH entry, classify:
- **UNCHANGED** — evidence has no bearing.
- **CONTRADICTED** — feature chose a different approach / fixed the root cause / relaxed the constraint. State the new truth and cite sub-feature or SHA.
- **NARROWED** — still holds but scope/threshold/exceptions changed. Cite what changed.
- **STALE** — references files, types, error messages that were renamed/moved/removed. Cite what moved.

Default to UNCHANGED. Be specific — name sub-features or SHAs.

### Dimensions

- **Architecture & Decisions** — scope: structural changes (feature scope, sub-issue notes, commit messages, files changed).
- **Patterns** — scope: implementation changes (sub-issue notes, diffs summary, commit messages).
- **Gotchas** — scope: fixes and quality (bug sub-features, optimize results, test results, reverts).
- **Constraints** — scope: requirements and measurements (success criteria, test perf data, optimize measurements, constraint-violation bugs).

### Return contract

Per entry, one line:

```
<entry-title>: <UNCHANGED | CONTRADICTED | NARROWED | STALE> — <one-line reason; cite SHA / sub-feature for non-UNCHANGED>
```

## Cross-reference re-evaluation

You are re-evaluating entries whose cross-reference targets were just flagged by the dimensional pass.

Your input will include:
- **Flagged entry + classification** (CONTRADICTED | NARROWED | STALE from the dimensional pass)
- **Referencing entries** — entries that cite the flagged entry via `Motivated by:`, `Prevents:`, or `Motivated:`

For EACH referencing entry, classify: `UNCHANGED | CONTRADICTED | NARROWED | STALE`.
Reason: the underlying motivation/prevention target shifted — does the referencing entry still hold?

### Return contract

Same per-entry line format as the dimensional detector.
