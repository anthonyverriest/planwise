---
description: "Distill a completed feature into the project knowledge base"
---

# Memo — Knowledge Base Update

Distill a completed feature's learnings into the project knowledge base. Runs after a feature is done.

**Assumed context:** this workflow runs inside a fresh jj workspace created by `pw claude`. Concurrent runs are isolated by workspace — each `pw claude` session has its own `@`. No cross-session contention.

Artifacts maintained per run:
- `planwise/knowledge/<domain>.md` — narrative knowledge for humans
- `planwise/knowledge/<domain>.jsonl` — typed records for agents (one entry per line)
- `planwise/knowledge/<domain>.eval.md` — developer questions used to measure KB quality
- `planwise/knowledge/INDEX.md` — grep-optimized domain map
- `planwise/knowledge/_lessons.md` — planning lessons (distinct from domain truth)

The knowledge base is a living artifact — refactored like code, not archived like documents. Each domain file must pass the **cold start test**: an agent or developer reading only this file can act correctly in the domain without chasing other sources. Phase 4.5 verifies this with an isolated reader.

## Target: Feature $ARGUMENTS

## Writing principles

Every entry in the knowledge base serves two audiences: a developer scanning for context and an agent consuming it as prompt context. Seven principles govern all writing: density, evergreen language, self-contained entries, concrete over abstract, `[critical]` sparingly (<20% of entries), cross-links (`Motivated by` / `Prevents` / `Motivated`), and provenance (every entry carries `source: <sha> | <issue-id>`). Full definitions live in `src/planwise/workflows/_memo/distill.md § **Writing principles**` — the distillation subagents read them directly. The Phase 4 Step 5 entry-quality gate enforces them on the composed output.

## Phase 1: Validate readiness

```bash
planwise view $ARGUMENTS --field type
planwise view $ARGUMENTS --field status
```

**Guards:**
- Type must be `feature`. If not → stop: `$ARGUMENTS is not a feature.`
- Status must be `done` or `in-review`. If `in-review`, warn: `Feature $ARGUMENTS is in-review, not done. Proceeding — knowledge may be incomplete.` Any other status → stop: `Feature $ARGUMENTS is not complete (status: <status>). Finish the feature first.`

**Evidence check (warn-only, never block):**

```bash
TEST_COMMITS=$(jj log -r 'description(glob:"test:*") & dev@origin..@' --no-graph -T 'change_id.short() ++ "\n"' | wc -l)
OPT_COMMITS=$(jj log -r 'description(glob:"optimize:*") & dev@origin..@' --no-graph -T 'change_id.short() ++ "\n"' | wc -l)
```

- Both zero → emit: `Thin evidence: no test: or optimize: commits found for this feature. Distillation will rely on implementation commits and op-log only; Phase 6 cluster gate (≥2 signal classes) may under-trip.`
- Exactly one zero → emit: `Partial evidence: no <test|optimize> commits found. The <quality-gap|approach-wrong> signal class will be absent from Phase 6.`
- Both present → proceed silently.

Record the evidence state for Phase 7 — the report carries it forward so future /memo runs know the KB entry was built on partial signal.

## Phase 1.5: Scale gate

Right-size the pipeline to the feature. Read once:

```bash
planwise list --children-of $ARGUMENTS --type sub-feature
planwise list --children-of $ARGUMENTS --type bug
jj log -r 'description(glob:"optimize:*") & dev@origin..@' -T builtin_log_oneline
```

Classify:

- **Trivial** — 1 sub-feature, 0 bug sub-features, 0 optimize commits. Run: single combined-lens subagent (Phase 3 folded to 1 call), skip Phase 3.5 sweep, skip Phase 6 rewrite reviewer. Phases 4, 4.5, 5, 5.5, 6 (signal collection), 6.5, 7 still run.
- **Standard** — 2-6 sub-features. Run full pipeline.
- **Large** — 7+ sub-features OR touches >1 domain. Run full pipeline + per-domain split in Phase 4 Step 4.

Record the classification; Phase 7 reports it.

## Phase 2: Gather sources

Collect the feature's artifacts and the existing knowledge base state.

### Step 1: Read the feature and sub-features

```bash
planwise view $ARGUMENTS
planwise list --children-of $ARGUMENTS --type sub-feature
planwise list --children-of $ARGUMENTS --type bug
planwise list --children-of $ARGUMENTS --type uat
planwise view <sub-feature-id>    # for each
```

Record: feature title, user story, success criteria, scope, assumptions & risks; per sub-feature title + requirements + implementation notes + acceptance criteria + notes; for bugs: what broke, root cause, fix; for UAT: what was tested, pass/fail.

### Step 2: Walk jj history for the feature change

```bash
jj bookmark list --all-remotes | grep -E '^(feat|fix)/'
jj log -r 'dev@origin..@' -T builtin_log_oneline --stat
```

If the bookmark is already merged into `dev`:

```bash
jj log -r 'description(glob:"*'"$ARGUMENTS"'*") & ::dev@origin & merges()' -T builtin_log_oneline --stat
```

Extract commit SHAs (needed for `source:` fields), commit descriptions (encode decisions), reverts and abandons (encode gotchas), and `optimize:` commits (what was fixed post-implementation).

### Step 3: Read optimize and test artifacts

```bash
jj log -r 'description(glob:"optimize:*") & dev@origin..@' -T builtin_log_oneline
jj log -r 'description(glob:"test:*") & dev@origin..@' -T builtin_log_oneline
planwise view <sub-feature-id>    # check notes for optimize/test reports
```

Record optimize verdict (converged/stuck/stopped) + iteration count, test findings, dimensions that scored poorly.

### Step 3b: Mine the jj operation log for discarded work

**Pure knowledge-base signal that git cannot provide.** jj's op log preserves every repo mutation — including changes abandoned, rewritten, or reverted during implementation. These are where gotchas live.

```bash
jj op log --limit 200 --no-graph -T 'id.short() ++ " " ++ description ++ "\n"'
jj op log --limit 200 --patch     # read-only diff per op
```

Scope to this feature's timeline. Look for `abandon` (discarded approaches), `rewrite`/`squash`/`rebase` (rework, conflict hotspots), `restore` (rollbacks). Multiple ops on the same change-id signal repeated attempts.

Read abandoned change content directly while it's still indexed:

```bash
jj show <abandoned-change-id>
```

Do **not** use `jj op restore` as preview — it mutates state. `jj op log --patch` is the read-only path.

Record: abandoned approaches → *Gotchas* and *Rejected*; conflict hotspots → *Gotchas* and *Constraints*; rework patterns → *Decisions* (final approach with rejected alternatives).

### Step 4: Identify target domain(s) and read existing knowledge

A domain maps to a bounded context (e.g., `auth`, `payments`, `ingestion`). Most features touch one domain; some touch two. More than two suggests the feature was too broad — pick the primary.

```bash
ls planwise/knowledge/
cat planwise/knowledge/<domain>.md       # if exists
cat planwise/knowledge/<domain>.eval.md  # if exists
```

Subagents need current state to merge against.

## Phase 3: Distill and merge

Launch subagents in one message. **Trivial** scale: one combined subagent covers all sections. **Standard/Large** scale: three parallel subagents.

The merge protocol (detect contradictions → keep / update / remove / add, with `[SUPERSEDED]` and `[VERIFY]` flagging) is defined in `_memo/distill.md § **Merge protocol**` — subagents apply it. The orchestrator resolves remaining flags in Phase 4 Step 1.

### Dispatch — distillation subagents (Agent tool, general-purpose)

**Standard / Large scale** (three parallel dispatches):

> Read `src/planwise/workflows/_memo/distill.md` § **Writing principles**, § **Merge protocol**, § **Subagent 1: Architecture, Decisions, Patterns, Rejected**.
> Inputs:
> - Feature: `<title, user story, scope>`
> - Sub-issues: `<titles + implementation notes>`
> - Git log: `<commit messages + SHAs + file changes>`
> - Bug fixes: `<what broke and why>`
> - Abandoned / rejected approaches (from jj op log): `<summary>`
> - Existing knowledge (if any): `<full sections 1, 2, 3, 7>`
> Return merged output for the four sections per the protocol.

> Read `src/planwise/workflows/_memo/distill.md` § **Writing principles**, § **Merge protocol**, § **Subagent 2: Gotchas & Constraints**.
> Inputs:
> - Feature: `<title, scope, assumptions & risks>`
> - Sub-issues: `<titles + requirements>`
> - Bug fixes: `<full descriptions and fixes>`
> - Optimize results: `<what was fixed, what was evolved, remaining items>`
> - Test results: `<bugs found, crashes, what held up>`
> - Git history: `<reverts, multi-attempt commits, SHAs>`
> - Existing knowledge (if any): `<full sections 4, 5>`
> Return merged output for sections 4 and 5 per the protocol.

> Read `src/planwise/workflows/_memo/distill.md` § **Writing principles**, § **Merge protocol**, § **Subagent 3: Preamble & Connections**.
> Inputs:
> - Feature: `<title, user story, success criteria, scope>`
> - Sub-issues: `<titles + dependencies>`
> - Files changed: `<list from git>`
> - Existing knowledge (if any): `<preamble and section 6>`
> Return merged Preamble and Connections per the protocol.

**Trivial scale** (single dispatch):

> Read `src/planwise/workflows/_memo/distill.md` § **Writing principles**, § **Merge protocol**, § **Trivial scale: combined subagent**.
> Inputs: union of the three input lists above.
> Return all sections per the protocol.

## Phase 3.5: Contradiction sweep

**Skip this phase if no existing knowledge file was found — nothing to contradict.** **Skip at Trivial scale** — the single subagent already covers the file end-to-end.

The Phase 3 subagents focus on their lens and catch obvious contradictions. They miss entries indirectly invalidated — a constraint silently relaxed, a gotcha whose root cause was fixed as a side effect, a decision whose rationale no longer holds. This sweep challenges every entry the subagents **kept unchanged**.

### Step 1: Build the kept-entries list

Collect entries carried forward unchanged. Exclude entries already marked `[SUPERSEDED]`, `[VERIFY]`, updated, or removed.

### Step 2: Dimensional pre-filter (parallel)

Each section can only be contradicted by specific evidence classes. Split into focused calls with bounded context. Launch in parallel. Skip any dimension with zero kept entries. Four dimensions: Architecture & Decisions, Patterns, Gotchas, Constraints — scope definitions live in `_memo/sweep.md § **Dimensions**`.

### Dispatch — contradiction detectors (one per non-empty dimension, parallel)

> Read `src/planwise/workflows/_memo/sweep.md` § **Dimensional contradiction detector**.
> Inputs:
> - Scope: `<structural changes | implementation changes | fixes + quality | requirements + measurements>`
> - Evidence: `<paste relevant Phase 2 material for this scope>`
> - Entries to verify: `<paste kept-unchanged entries for this dimension>`
> Return per-entry classifications per § **Return contract**.

### Step 3: Cross-reference pass

The dimensional filter is cheap but leaky — a gotcha killed by a pattern change lives in different scopes. For any entry the dimensional filter returned CONTRADICTED / NARROWED / STALE, locate entries that reference it (via `Motivated by`, `Prevents`, `Motivated`) and dispatch:

> Read `src/planwise/workflows/_memo/sweep.md` § **Cross-reference re-evaluation**.
> Inputs:
> - Flagged entry + classification: `<paste>`
> - Referencing entries: `<paste>`
> Return per-entry classifications per § **Return contract**.

This pass is small (only entries with live cross-refs to a flagged target) and catches contradictions the dimensional split misses.

### Step 4: Apply sweep results

- **CONTRADICTED**: rewrite with the new truth, or remove if the concept no longer applies. Update `source:` to cite the evidence.
- **NARROWED**: update to reflect the new scope or exceptions. Preserve what's still accurate.
- **STALE**: verify referenced code (Glob/Grep). Update refs if moved; remove entry if removed.

Fold corrections into subagent outputs before Phase 4.

## Phase 4: Compose

### Step 1: Resolve flags

Review remaining `[SUPERSEDED]` and `[VERIFY]` flags:
- `[SUPERSEDED]` — remove old entry; the subagent already wrote the replacement or determined obsolescence.
- `[VERIFY]` — read the relevant code or issue. Keep / update / remove based on findings.

Do NOT leave flags in the final document.

### Step 2: Cross-reference entries

Check internal consistency:
- Every `Motivated by:` in Decisions points to a real Constraint or Gotcha.
- Every `Prevents:` in Patterns points to a real Gotcha.
- Every `Motivated:` in Gotchas points to a real Decision.
- Connections list types/interfaces present in Decisions or Architecture.
- Every entry has a `source:` field.

Fix broken references: add the missing entry or drop the reference. Phase 5.5 will enforce bidirectional integrity — any dangling reference at that point is a hard fail.

### Step 3: Determine domain name and tags

- **Domain name:** lowercase, hyphenated (e.g., `auth`, `event-ingestion`).
- **Tags** (3-6): lowercase, hyphenated, derived from key technologies, patterns, or cross-cutting concerns. No generic tags (`feature`, `code`). Merge with existing.

### Step 4: Write or update the knowledge file

```bash
mkdir -p planwise/knowledge
```

Target path: `planwise/knowledge/<domain>.md`. Template:

```markdown
---
domain: <domain-name>
tags: [<tag1>, <tag2>, <tag3>]
features: [<N>, <N>]
updated: <YYYY-MM-DD>
eval_score: {green: N, yellow: N, red: N}   # populated by Phase 4.5
---

# <Domain Name>

<Preamble from Subagent 3>

## 1. Architecture
<From Subagent 1>

## 2. Decisions
<From Subagent 1 — self-contained with rationale, consequences, cross-refs, source>

## 3. Patterns
<From Subagent 1 — trigger condition, mechanism, cross-refs, source>

## 4. Gotchas
<From Subagent 2 — symptom, root cause, prevention, cross-refs, source>

## 5. Constraints
<From Subagent 2 — measurement, origin, failure consequence, source>

## 6. Connections
<From Subagent 3 — depends on, shared types, deferred work>

## 7. Rejected
<From Subagent 1 — approach, why rejected, reconsideration condition, source>
```

**Retrieval convention:** consumers grep `^## [0-9]` to get a section TOC with line numbers, then read only the needed section. Never `cat` the full file.

If updating, preserve `features:` (append the new feature number) and set `updated:` to today.

**Large-scale per-domain split:** if the feature touches >1 domain, split into separate files per domain. Each must pass the cold start test independently. Update the index accordingly.

### Step 5: Entry-quality gate

Verify before proceeding to Phase 4.5:
- Every entry names specific files, functions, types, or error messages — nothing reads like generic advice.
- Every Decision includes what was rejected and why.
- Every Gotcha includes an observable symptom.
- Every Constraint is measurable.
- Every entry has a `source:` field.
- No temporal language, feature-specific framing, or placeholder language.
- `[critical]` markers are <20% of entries.
- All cross-references resolve to real entries.
- No duplicate entries covering the same knowledge from different angles.
- Architecture is a navigational map, not documentation.
- Preamble is 2-3 sentences.

Any failure: fix before Phase 4.5.

## Phase 4.5: Adversarial reader + eval harness

The entry-quality gate is self-graded by the writer. Phase 4.5 introduces an isolated reader — an agent that has **only the new domain file** as context and must plan concrete tasks from it. Every gap the reader reports is a concrete deficiency a checklist cannot catch.

### Step 1: Assemble the task set

**Eval questions.** Read (or create) `planwise/knowledge/<domain>.eval.md`:

```bash
cat planwise/knowledge/<domain>.eval.md    # if exists
```

If the file exists, use its existing questions unchanged. If not, seed with 5 developer-scoped questions derived from the domain's preamble and this feature's scope — questions a future developer or agent would plausibly ask before changing this domain. Examples: "How would I add rate-limiting to the existing endpoints?", "Where does retry logic live and what are its bounds?", "What breaks if I change the event schema?"

Write the eval file:

```markdown
---
domain: <domain-name>
updated: <YYYY-MM-DD>
---

# Eval questions for <domain>

Used by /memo Phase 4.5 to stress-test the domain knowledge file. Edit freely — questions represent what future developers and agents will ask.

- <question 1>
- <question 2>
...
```

**Past-feature hypotheticals.** From the domain's `features:` frontmatter, sample 2 feature titles (excluding the current one). If fewer than 2 exist, synthesize one plausible scenario from preamble + scope and flag it as synthetic.

### Step 2: Run the adversarial reader

Dispatch one subagent with ONLY the new domain file as context:

> Read `src/planwise/workflows/_memo/reader.md` § **Adversarial reader**.
> Inputs:
> - Tasks:
>   - `<eval question 1>`
>   - `<eval question 2>`
>   - ...
>   - Plan how you would implement: `<past feature title 1>`
>   - Plan how you would implement: `<past feature title 2>`
> - Knowledge file: `<paste full domain file>`
> Return per § **Return contract**.

### Step 3: Apply results

- **Any red rating** → revise the file to close the gap. Add the missing entry (with source), then re-run the reader on just the red tasks until green or yellow.
- **Yellow ratings** → log to Phase 7 report as known minor gaps. Do not block.
- **All green** → record and proceed.

Record `eval_score: {green: N, yellow: N, red: 0}` in the frontmatter. Compare to the previous run's `eval_score` (if any) — a regression (fewer greens, more reds) is a red flag the distillation lost information.

## Phase 5: Update the index

The index is a grep-optimized domain map. Consumers grep INDEX.md to discover which domain file contains a concept, then grep the domain file for section offsets.

### Retrieval convention

```bash
grep -i "idempotent" planwise/knowledge/INDEX.md           # find domain + section
grep -n '^## [0-9]' planwise/knowledge/<domain>.md         # section TOC with line numbers
```

### If `INDEX.md` does not exist, create it:

```markdown
# Knowledge Base

Living knowledge about each domain. Each file contains current truth — architecture, decisions, patterns, gotchas, constraints, connections, rejected approaches. Updated by `/memo` after each feature.

Retrieval: `grep -i "<keyword>" planwise/knowledge/INDEX.md` → find domain + section, then `grep -n '^## [0-9]' planwise/knowledge/<domain>.md` for offsets. Typed queries: use `<domain>.jsonl`.

## Domains
```

### Add or update the domain entry:

```markdown
- **[<Domain Name>](./<domain>.md)** — <preamble summary> | `<tag1>` `<tag2>` `<tag3>`
  - Decisions: <comma-separated titles>
  - Patterns: <comma-separated titles>
  - Gotchas: <comma-separated titles>
  - Constraints: <comma-separated titles>
  - Rejected: <comma-separated titles>
```

Maintain alphabetical order. Entry titles must match the bold titles in the domain file exactly — they are grep targets.

## Phase 5.5: Emit JSONL twin & enforce link integrity

The markdown is for humans. Agents consume a typed JSONL twin — one line per entry across all sections — for structured retrieval without markdown parsing.

### Step 1: Emit `<domain>.jsonl`

Re-read the finalized `<domain>.md` and emit `planwise/knowledge/<domain>.jsonl`. One line per entry in sections 1-7:

```json
{"id":"<domain>/<section>/<title-slug>","domain":"<domain>","section":"<section-name>","title":"<title>","body":"<full entry body, markdown preserved>","critical":<bool>,"refs":[<referenced-entry-ids>],"source":"<sha>|<issue-id>","updated":"<YYYY-MM-DD>"}
```

- `id` — stable: `<domain>/<section>/<kebab-slug-of-title>`.
- `refs` — resolve every `Motivated by:` / `Prevents:` / `Motivated:` to the target entry's id. Empty list if none.
- `critical` — true if entry is marked `[critical]`, else false.
- `source` — mirror the `source:` line from the entry.

Architecture and Preamble are free-form; emit each as a single entry with `title: "preamble"` / `title: "architecture"` and empty `refs`.

### Step 2: Enforce bidirectional link integrity

For every entry with non-empty `refs`, verify each referenced id exists in the JSONL. For any dangling ref → **hard fail**: report the broken reference, return to Phase 4 Step 2, fix, re-emit.

For every entry referenced by another, append the referencing entry's id to its `refs` list (back-reference). The JSONL is rewritten once both forward and back refs are complete. This makes orphan detection cheap: any future entry removal that breaks a back-reference surfaces immediately.

### Step 3: Sanity check

```bash
wc -l planwise/knowledge/<domain>.jsonl    # entry count
grep -c '^## ' planwise/knowledge/<domain>.md   # section count
```

Entry count should roughly match bullet count in the markdown. Spot-check 2 entries round-trip correctly.

## Phase 6: Plan retrospective

Distill generalizable planning lessons from this feature's execution signals. Output: `planwise/knowledge/_lessons.md` — a separate artifact consumed only by `/plan` and `/brief` (leading `_` sorts it apart from domain files and keeps it out of the domain-concept grep path). Lessons are hypotheses; they strengthen through confirmation and graduate into domain knowledge when proven. Never duplicate entries across `_lessons.md` and domain files.

### Step 1: Collect the applied-lessons block

```bash
planwise view $ARGUMENTS
planwise view <sub-feature-id>    # for every sub-feature from Phase 2 Step 1 (any type)
```

Extract the `## Lessons Applied` block from the feature body (populated by `/plan` Phase 1) AND from every sub-feature body that contains one (populated by `/brief` for task sub-features, `/bug` for bug sub-features). Coding and UAT sub-features created by `/plan` inherit from the feature and do not carry their own block. Union across all sources; de-duplicate by title.

```bash
test -f planwise/knowledge/_lessons.md && cat planwise/knowledge/_lessons.md
```

### Step 2: Dispatch — lessons distiller (Agent tool, general-purpose)

> Read `src/planwise/workflows/_memo/lessons.md` § **Signal classes**, § **Applied-lesson scoring**, § **Cluster and gate**, § **Dedupe**, § **Promotion and pruning rules**, § **Entry format**, § **Quality gate**.
> Inputs:
> - Feature id: `$ARGUMENTS`
> - Domain tag: `<domain-name>`
> - Current feature number: `<integer, for age-based pruning>`
> - Planning-defect signals from Phase 2: `<sub-features added post-plan | bug sub-features | jj op log abandons & --patch discards | optimize verdicts | UAT failures | multi-attempt change-ids>`
> - Applied-lessons block (union, de-duplicated): `<paste>`
> - Current `_lessons.md` contents: `<paste, or "(file does not exist)">`
> Return per § **Return contract**.

### Step 3: Apply promotions

For each promotion candidate the subagent returned:

- **Standard / Large scale** — dispatch the rewrite reviewer:

  > Read `src/planwise/workflows/_memo/review.md` § **Rewrite reviewer (Phase 6 promotion)**.
  > Inputs:
  > - Original lesson entry: `<paste full active entry>`
  > - Proposed domain entry: `<paste subagent's proposed_entry>`
  > - Target section in domain file: `<paste the existing section>`
  > Return verdict per § **Return contract**.

  Only `approve` (or `revise` + applied revision) lands in the domain file and removes the entry from `## Active`.

- **Trivial scale** — direct rewrite, no reviewer. Apply the subagent's `proposed_entry` to the domain file; remove the entry from `## Active`.

Record every outcome (approved / revised / rejected / applied directly) for Phase 7.

### Step 4: Write `_lessons.md`

If the file does not exist, seed with this header before inserting the subagent's Active / Archive bodies:

```markdown
# Planning Lessons

Hypotheses about how /plan and /brief should approach work in this codebase, distilled from execution signals by /memo Phase 6. Consumed by /plan Phase 1 and /brief Phase 1. Lessons strengthen through confirmation and graduate into domain knowledge when `successful_applications >= 3 AND failed_applications == 0`.

Retrieval: grep -i -B1 -A5 "<keyword-or-domain-tag>" planwise/knowledge/_lessons.md

## Active
```

Append `## Archive` section below. If the subagent returned `Outcome: No lessons extracted` AND no scoring updates apply AND the file already exists, leave it untouched — record "Nothing to save." for Phase 7.

## Phase 6.5: Cross-domain reflection (cadence-gated)

Single-feature `/memo` cannot see patterns spanning domains. This phase runs periodically to surface them.

### Cadence gate

Run ONLY when:
- This feature brings the domain's `features:` count to a multiple of 5, OR
- This feature touched >1 domain.

Otherwise skip. Record "skipped (cadence: <reason>)" in Phase 7. Most runs skip.

### Reflection call

Collect per-domain snapshot (frontmatter + section headings + entry titles only — no bodies, to bound context):

```bash
for f in planwise/knowledge/*.md; do
  [[ "$f" == *INDEX.md || "$f" == *_lessons.md ]] && continue
  head -n 10 "$f"                    # frontmatter
  grep -n '^## \|^- \*\*' "$f"       # section headings + entry titles
done
```

Dispatch one subagent:

> Read `src/planwise/workflows/_memo/review.md` § **Cross-domain reflection (Phase 6.5)**.
> Inputs:
> - Per-domain snapshot: `<paste the collected output>`
> Return proposals per § **Return contract**. Findings are PROPOSALS only — no file changes in this phase.

### Apply results

Reflection findings go to the Phase 7 report only. No automatic file changes in this phase — cross-domain edits happen in subsequent human-directed work (a follow-up feature, a dedicated consolidation task).

## Phase 6.9: Anchor the memo bookmark

Knowledge-file edits produced by this run need somewhere to land. Anchor a `memo/<domain>` bookmark on the highest non-empty change so the epilogue publishes the memo commits:

```bash
MEMO_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
jj bookmark create memo/<domain> -r "$MEMO_HEAD" || jj bookmark set memo/<domain> -r "$MEMO_HEAD"
```

If the revset returns empty (no knowledge changes — distillation produced no deltas), skip this step.

## Phase 7: Report

```
Knowledge base updated for Feature $ARGUMENTS.

Scale:   <trivial | standard | large>
Evidence: test=<N commits> optimize=<N commits>  <full | partial (<missing class>) | thin>
Domain:  <domain-name> (or list if Large split)
File:    planwise/knowledge/<domain>.md
Twin:    planwise/knowledge/<domain>.jsonl (N entries)
Action:  <created | updated>

Sections:
  Architecture:  <created | updated | unchanged>
  Decisions:     N entries (M new, K updated, J removed) [P critical]
  Patterns:      N entries (M new, K updated, J removed)
  Gotchas:       N entries (M new, K updated, J removed)
  Constraints:   N entries (M new, K updated, J removed) [P critical]
  Connections:   <created | updated | unchanged>
  Rejected:      N entries (M new, K updated, J removed)

Cross-references: N links between entries
Contradiction sweep: N entries verified, M corrections (one-line summaries)
  Dimensional pre-filter: N flagged
  Cross-reference pass:   M additional flags surfaced
Link integrity: all forward and back-references resolved

Adversarial reader (Phase 4.5):
  Tasks run:    N eval questions + M past-feature hypotheticals
  Eval score:   green=N yellow=N red=N (prev: green=N yellow=N red=N)
  Revisions:    N iterations to close red gaps
  Minor gaps:   <list yellow findings, if any>

Tags: <tag1>, <tag2>, <tag3>

Planning lessons (planwise/knowledge/_lessons.md):
  Signals collected: N (scope-miss=A, risk-miss=B, approach-wrong=C, quality-gap=D, estimation-miss=E)
  Usefulness feedback (from originating plan's Lessons Applied):
    Applied:          N lessons retrieved and referenced in the plan
    Successful:       N (defect class did not recur — list titles)
    Failed:           N (defect class recurred despite lesson — list titles with reason)
    Contract-miss:    N lessons plausibly unretrieved (/plan did not emit Lessons Applied block — list titles)
  Lessons added:      N new entries
  Lessons confirmed:  N existing entries strengthened (list titles with new confirmations count)
  Lessons promoted:   N entries graduated into domain files (list: title → target section, rewrite review outcome)
  Lessons archived:   N (net failure: F | untriggered age: A — list titles with reason)
  Outcome (if none):  "No lessons extracted — signals did not converge"

Cross-domain reflection (Phase 6.5):
  Status: <ran | skipped (cadence: <reason>)>
  Recurring patterns:   N proposals (list)
  Terminology drift:    N proposals (list)
  Redundant gotchas:    N proposals (list)
  (proposals only — no automatic changes)

This knowledge is available as context for future /plan sessions.
To browse: grep -n '^## [0-9]' planwise/knowledge/<domain>.md
To search: grep -i "<keyword>" planwise/knowledge/INDEX.md
To query: jq 'select(.critical)' planwise/knowledge/<domain>.jsonl
To review lessons: grep -i "<trigger>" planwise/knowledge/_lessons.md
```
