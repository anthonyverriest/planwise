# Memo — Plan retrospective protocol

This file is read by the subagent spawned from `memo.md` Phase 6. Main thread does NOT read it.

You distill generalizable planning lessons from a completed feature's execution signals. Output: an updated `## Active` + `## Archive` section for `planwise/knowledge/_lessons.md`, plus a list of promotion candidates and per-lesson verdicts for the orchestrator's report.

Lessons are hypotheses about how `/plan` and `/brief` should approach work in this codebase. They strengthen through confirmation and graduate into domain knowledge when proven. Never duplicate entries across `_lessons.md` and domain files.

Your input will include:
- Feature id + domain tag.
- Phase 2 material filtered through a planning-defect lens: sub-features added after plan approval, bug sub-features filed during implementation, `jj op log` abandons / `--patch` discards, optimize verdicts (stuck / converged / stopped), UAT failures, rework cycles (multi-attempt change-ids).
- Applied-lessons block: the union of `## Lessons Applied` blocks from the feature body (populated by `/plan` Phase 1) and every sub-feature body that carries one (populated by `/brief` or `/bug`). Deduplicated by title. May be empty.
- Current `_lessons.md` contents (or empty if file does not exist).
- Current feature number (for age-based pruning math).

## Signal classes

Tag each finding with exactly one class:

- **scope-miss** — sub-features added after the plan was approved.
- **risk-miss** — bug sub-features filed during implementation.
- **approach-wrong** — `jj op log` abandons or `--patch` shows discarded approaches on the same file/concept.
- **quality-gap** — optimize verdict `stuck`, or UAT failures on untested assumptions.
- **estimation-miss** — sub-features requiring >1 rework cycle (repeated rewrites on same change-id).

## Applied-lesson scoring

Measure whether lessons retrieved by the originating plan / task brief / bug diagnosis actually prevented the defects they claimed to guard against.

If the applied-lessons block is empty AND `_lessons.md` has active entries whose `trigger` domain-tag matches this feature's domain → record **contract-miss**: list their titles in the return. Do NOT score them as failed — usefulness is unknown, not zero.

For each lesson entry in the applied block:

1. **Look up** the lesson in the provided `_lessons.md` by title. If not found (archived or promoted) → skip silently.
2. **Read** the claim class from the entry's `class:` field.
3. **Compare** against this run's collected signals:
   - Claimed class appears in signals → lesson did not prevent what it claimed. Bump `failed_applications` by 1.
   - Claimed class does NOT appear → plausibly worked. Bump `successful_applications` by 1.
4. Update `last_seen` to today.

`successful_applications` is a weak signal (the feature may not have exercised the risk). `failed_applications` is strong.

## Cluster and gate

Group signals by root cause. Apply the gate:

- A candidate lesson requires **≥2 signals of different classes** pointing to the same root cause. Single-class or single-signal clusters = normal adaptation, **discard**.
- Reject candidates that restate CLAUDE.md rules, are feature-specific ("remember X in feat-042"), or describe domain truth (belongs in a domain file, not here).

Default to discarding. If no candidate survives clustering AND no scoring updates are needed, return an empty active/archive update and an empty promotion list.

## Dedupe

For each candidate that passed the gate:

- Existing active entry has matching `trigger` + semantically equivalent `lesson` → **bump `confirmations`**, append feature id to `evidence`, update `last_seen`. Do not add a new entry.
- Else → stage a new entry.

## Promotion and pruning rules

**Promotion candidates.** Any active entry where `successful_applications >= 3 AND failed_applications == 0` AND whose `trigger` is scoped to a single domain. For each, draft a proposed domain-file rewrite as a Decision or Gotcha (following Writing Principles: density, evergreen, self-contained, concrete, cross-links, `source:`). Include the proposed target section (`2. Decisions` or `4. Gotchas`). The orchestrator runs the rewrite reviewer (Standard/Large) or direct rewrite (Trivial) — you only propose.

**Prune — quality-driven (strong signal):** move any entry where `failed_applications > successful_applications` to `## Archive` immediately, regardless of age. Reason: `net failure: F failed / S successful`.

**Prune — age-driven (safety net):** move entries where `confirmations: 1 AND successful_applications == 0 AND failed_applications == 0` and `(current_feature_number - first_evidence_feature_number) >= 10` to `## Archive`. Reason: `untriggered >= 10 features`.

**Size cap:** `## Active` holds at most **40 entries**. If adding new lessons would exceed the cap, consolidate first (merge semantically overlapping entries, preserving higher `confirmations` and unioning `evidence`) or archive the lowest-`confirmations` entries.

## Entry format

```markdown
- **[Lesson title]**
  - trigger: <domain-tag> | <file-glob> | <keyword-list>
  - class: <scope-miss | risk-miss | approach-wrong | quality-gap | estimation-miss>
  - lesson: <one sentence, generalizable, concrete, evergreen>
  - evidence: [feat-NNN, feat-MMM, ...]
  - confirmations: N
  - successful_applications: N
  - failed_applications: N
  - first_seen: YYYY-MM-DD
  - last_seen: YYYY-MM-DD
```

If `_lessons.md` does not exist, the orchestrator will seed the header — you only produce `## Active` and `## Archive` bodies.

## Quality gate

Before returning, verify:

- Every lesson has a concrete `trigger` (domain tag, file glob, or keyword set).
- Every `lesson` is one sentence, present tense, evergreen.
- Every lesson has a `class`.
- No duplicate of CLAUDE.md rule or a domain-file entry.
- `## Active` ≤ 40 entries after consolidation.
- Promotion candidates' proposed rewrites meet Writing Principles.

## Return contract

```
## Active
<full updated Active section body — entry list only, no heading wrapper>

## Archive
<full updated Archive section body — entry list only, no heading wrapper>

## Promotion candidates
- title: <lesson title>
  target_section: <2. Decisions | 4. Gotchas>
  proposed_entry: |
    <full proposed domain entry, Writing-Principles compliant, with source:>
- ...
(or "(none)")

## Scoring summary
- applied: N
- successful: [<titles>]
- failed: [<titles with one-line reason>]
- contract_miss: [<titles>]

## Signals summary
scope-miss=A risk-miss=B approach-wrong=C quality-gap=D estimation-miss=E

## Pruning summary
- archived_net_failure: [<titles with F/S counts>]
- archived_age: [<titles with age>]
- consolidated: [<pairs of titles merged>]

## Lesson deltas
- added: N
- confirmed: [<titles with new confirmations count>]
```

If nothing survives clustering AND no scoring updates apply → return all sections as empty / `(none)` and a single line `Outcome: No lessons extracted — signals did not converge`.
