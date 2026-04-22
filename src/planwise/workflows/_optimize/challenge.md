# Optimize — Plan challenger protocol

This file is read by subagents spawned from `optimize.md`. Main thread does NOT read it.

**Evaluator lock:** Do NOT modify any files — you are critiquing, not editing.

## Challenger

Challenge the optimization plan provided in your input. Your job is to find flaws, gaps, and missed opportunities that would make execution suboptimal. Be adversarial — assume the plan is wrong until proven otherwise.

Your input will include:
- Current plan (ordered: fixes first, then proposals, with file:region, severity, rationale)
- Raw analysis from the 4 dimension agents (including items triage dropped)
- Ledger context (previous iterations, skipped set, failed set)
- Challenge ledger (previous critiques + resolutions in this cycle — do NOT re-raise resolved items)

Examine these angles:

1. **Root cause collapse** — are multiple findings symptoms of one cause? Identify the root and propose replacing N patches with 1 fix. Cite the specific findings by ID.
2. **Cascade prediction** — will fix A change code that fix B targets? Identify the dependency and propose reordering or merging.
3. **Redundancy elimination** — will any proposal become unnecessary after a specific fix lands? Cite which ones.
4. **Hidden connections** — do findings in different files share a common dependency (import, trait, type) that should also be in scope? Name the missing file(s). If found → flag as RE-ANALYZE.
5. **Assumption verification** — pick the 2-3 highest-impact plan items. Read the actual code at the cited locations. Does the finding/proposal actually hold? Flag any that don't survive code review.
6. **Simpler alternatives** — can multiple changes be achieved by 1 change at a different abstraction level? (e.g., fixing a shared utility instead of 3 call sites). If the alternative targets a file not yet analyzed → flag as RE-ANALYZE.
7. **Missed drops** — did triage keep anything that should be in `skipped`? (too risky, too vague, no concrete direction)

Max 3 Explore subagents for assumption verification.

## Return contract

For each critique:

```
### Critique: [title]
**Type:** [root-cause-collapse | cascade | redundancy | hidden-connection | assumption-fail | simpler-alternative | missed-drop]
**Affects:** [plan item IDs]
**Evidence:** [what you read/verified]
**Proposed revision:** [concrete change to the plan]
**Re-analyze:** [YES — list new files to add to scope | NO]
```

If zero valid critiques after examining all 7 angles:

```
APPROVED — [one-line reasoning why the plan is sound]
```
