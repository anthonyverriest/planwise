---
description: "Distill a completed feature into the project knowledge base"
---

# Memo — Knowledge Base Update

Distill a completed feature's learnings into the project knowledge base. Runs after a feature is done.

Artifacts maintained per run:
- `planwise/knowledge/<domain>.md` — narrative knowledge for humans
- `planwise/knowledge/<domain>.jsonl` — typed records for agents (one entry per line)
- `planwise/knowledge/<domain>.eval.md` — developer questions used to measure KB quality
- `planwise/knowledge/INDEX.md` — grep-optimized domain map
- `planwise/knowledge/_lessons.md` — planning lessons (distinct from domain truth)

The knowledge base is a living artifact — refactored like code, not archived like documents. Each domain file must pass the **cold start test**: an agent or developer reading only this file can act correctly in the domain without chasing other sources. Phase 4.5 verifies this with an isolated reader.

## Target: Feature $ARGUMENTS

## Writing principles

Every entry in the knowledge base serves two audiences simultaneously: a developer scanning for context and an agent consuming it as prompt context. These principles govern all writing in Phases 3-4.

**Density without compression.** Every sentence must carry information. No filler, no hedging, no "it should be noted that." But don't sacrifice clarity for brevity — a decision that takes 4 lines to explain properly is better than a 1-line entry that requires the reader to guess the rationale.

**Evergreen language.** Write in present tense about current state. No temporal references ("recently", "in the last sprint", "after the refactor"), no feature-specific framing ("this feature introduced"), no version numbers that will go stale. The entry describes what IS, not what CHANGED.

**Self-contained entries.** Each bullet must stand alone. A reader should never need to read another entry, another file, or the git history to understand what an entry says and why it matters. Include the "why" inline — don't point elsewhere for it.

**Concrete over abstract.** Name specific files, functions, types, error messages. "The payment webhook handler validates idempotency keys" beats "The system ensures idempotent processing." If an entry could apply to any codebase, it's too abstract.

**Signal salience.** Mark load-bearing entries `[critical]` — these are decisions, constraints, or gotchas where getting it wrong causes a production incident, data loss, or security vulnerability. Most entries are unmarked. Use `[critical]` sparingly — if more than ~20% of entries are critical, the signal is diluted.

**Link entries across sections.** When a decision exists because of a constraint, or a pattern exists to avoid a gotcha, say so inline: "Motivated by: *[constraint name]*" or "Prevents: *[gotcha name]*." Phase 5.5 enforces back-references automatically — if you name a target, it must exist.

**Provenance.** Every entry carries a trailing `source: <commit-sha-short> | <issue-id>` line. The source is the evidence backing the entry. Verification becomes deterministic: re-read the source, check whether the entry still reflects it. Entries without a source are rejected.

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

Launch subagents in one message. **Trivial** scale: one combined subagent produces all sections. **Standard/Large** scale: three parallel subagents as below. Every subagent receives the Writing Principles (see top of this file) — reject output that violates them.

### Merge protocol (all subagents)

1. **Detect contradictions.** For each existing entry, compare against the feature's evidence. If contradicted (different approach chosen, constraint relaxed, gotcha resolved), flag `[SUPERSEDED]` with a one-line reason.
2. **Keep** entries untouched by this feature.
3. **Update** entries where this feature adds nuance or new evidence — rewrite, don't append a note. Update the `source:` to reflect the newer evidence.
4. **Remove** entries the feature made obsolete (old version lives in git).
5. **Add** new entries. Every new entry must include `source: <sha-short> | <issue-id>`.

When uncertain whether an existing entry is still valid, keep it and flag `[VERIFY]` — Phase 4 resolves these.

### Subagent 1: Architecture, Decisions, Patterns, Rejected

```
You are writing for a project knowledge base that serves both human developers and AI agents.
Follow the Writing Principles strictly: density, evergreen language, self-contained entries, concrete over abstract, [critical] sparingly, cross-links, provenance on every new entry.

Feature: [title, user story, scope]
Sub-issues: [titles + implementation notes]
Git log: [commit messages + SHAs + file changes]
Bug fixes: [what broke and why]
Abandoned / rejected approaches (from jj op log): [summary]
Existing knowledge (if any): [full sections 1. Architecture, 2. Decisions, 3. Patterns, 7. Rejected]

Follow the merge protocol. List [SUPERSEDED] or [VERIFY] flags with reasons.

Produce merged output for four sections:

## 1. Architecture
How this domain works — the mental model a reader needs before touching this code.
- One paragraph: what the domain does and how data flows through it.
- Key components: name each with its file path and responsibility.
- Integration points: how this domain connects to others at the code level.

## 2. Decisions
Why things are the way they are. Entry format:
- **[Decision title]** — [What was chosen] over [what was rejected]. [Rationale: specific constraint or tradeoff]. [Consequence for future work]. Motivated by: *[constraint or gotcha name, if applicable]*. source: <sha> | <issue-id>

Only include decisions a future developer would benefit from knowing. Skip framework-default choices.

## 3. Patterns
Reusable approaches established or confirmed. Entry format:
- **[Pattern name]** — [What the pattern is and where it lives: @file_path]. [When to use: trigger condition]. [How it works: enough detail to apply]. Prevents: *[gotcha name, if applicable]*. source: <sha> | <issue-id>

Only include patterns not already in CLAUDE.md or project rulesets.

## 7. Rejected
Approaches considered and deliberately not taken in this domain. Prevents future agents from re-proposing dead ends. Entry format:
- **[Approach title]** — [What was considered]. [Why rejected: the specific constraint, cost, or failure that ruled it out]. [What it would look like if reconsidered: the condition that would flip the decision]. source: <sha> | <issue-id>

Populate from: abandoned approaches in jj op log, reverted commits, decisions' "rejected alternatives", and options explicitly ruled out in scope or assumptions & risks. Skip trivial rejections (syntax choices, formatting).
```

### Subagent 2: Gotchas & Constraints

```
You are writing for a project knowledge base that serves both human developers and AI agents.
Follow the Writing Principles strictly.

Feature: [title, scope, assumptions & risks]
Sub-issues: [titles + requirements]
Bug fixes: [full descriptions and fixes]
Optimize results: [what was fixed, what was evolved, remaining items]
Test results: [bugs found, crashes, what held up]
Git history: [reverts, multi-attempt commits, SHAs]
Existing knowledge (if any): [full sections 4. Gotchas, 5. Constraints]

Follow the merge protocol. List [SUPERSEDED] or [VERIFY] flags.

## 4. Gotchas
Things that will bite you in this domain. Entry format:
- **[Gotcha title]** — [Observable symptom]. [Root cause at the code level]. [How to avoid: specific prevention]. Motivated: *[decision name, if applicable]*. source: <sha> | <issue-id>

For each existing gotcha: did this feature fix the root cause? If yes, remove — the fix is in the code.

## 5. Constraints
Invariants, performance bounds, security boundaries. Only include constraints backed by evidence (optimize/test results, explicit requirements, production incidents). Entry format:
- `[critical]` **[Constraint title]** — [What the constraint is, measurable]. [Why it exists]. [What breaks on violation]. source: <sha> | <issue-id>
```

### Subagent 3: Preamble & Connections

```
You are writing for a project knowledge base that serves both human developers and AI agents.
Follow the Writing Principles strictly.

Feature: [title, user story, success criteria, scope]
Sub-issues: [titles + dependencies]
Files changed: [list from git]
Existing knowledge (if any): [preamble and 6. Connections]

Follow the merge protocol.

### Preamble
2-3 sentences describing what this domain is, its role in the system, and the core abstraction it provides. Not what any feature did — what this domain IS. Update only if this feature changed scope, role, or core abstraction.

## 6. Connections
- **Depends on:** [Domains/services this domain calls, imports, or requires — name the interface or contract]
- **Shared types:** [Types, schemas, or events crossing domain boundaries — only if misuse causes a bug grep alone wouldn't catch]
- **Deferred work:** [Items explicitly deferred — remove anything completed by this or prior features]

Consumers are discoverable via grep and go stale immediately; the KB tracks what this domain needs, not who uses it.
```

## Phase 3.5: Contradiction sweep

**Skip this phase if no existing knowledge file was found — nothing to contradict.** **Skip at Trivial scale** — the single subagent already covers the file end-to-end.

The Phase 3 subagents focus on their lens and catch obvious contradictions. They miss entries indirectly invalidated — a constraint silently relaxed, a gotcha whose root cause was fixed as a side effect, a decision whose rationale no longer holds. This sweep challenges every entry the subagents **kept unchanged**.

### Step 1: Build the kept-entries list

Collect entries carried forward unchanged. Exclude entries already marked `[SUPERSEDED]`, `[VERIFY]`, updated, or removed.

### Step 2: Dimensional pre-filter (parallel)

Each section can only be contradicted by specific evidence classes. Split into focused calls with bounded context. Launch in parallel. Skip any dimension with zero kept entries.

Each dimension call uses this template (substitute scope + entries):

```
You are a contradiction detector. Your ONLY job is to find entries no longer accurate given new evidence.

Scope: [structural changes | implementation changes | fixes + quality | requirements + measurements]
Evidence: [paste the relevant Phase 2 material for this scope]
Entries to verify: [paste kept-unchanged entries for this dimension]

For EACH entry, classify:
- UNCHANGED — evidence has no bearing.
- CONTRADICTED — feature chose a different approach / fixed the root cause / relaxed the constraint. State the new truth and cite sub-feature or SHA.
- NARROWED — still holds but scope/threshold/exceptions changed. Cite what changed.
- STALE — references files, types, error messages that were renamed/moved/removed. Cite what moved.

Default to UNCHANGED. Be specific — name sub-features or SHAs.
```

Dimensions:
- **Architecture & Decisions** — scope: structural changes (feature scope, sub-issue notes, commit messages, files changed).
- **Patterns** — scope: implementation changes (sub-issue notes, diffs summary, commit messages).
- **Gotchas** — scope: fixes and quality (bug sub-features, optimize results, test results, reverts).
- **Constraints** — scope: requirements and measurements (success criteria, test perf data, optimize measurements, constraint-violation bugs).

### Step 3: Cross-reference pass

The dimensional filter is cheap but leaky — a gotcha killed by a pattern change lives in different scopes. For any entry where the dimensional filter returned CONTRADICTED / NARROWED / STALE, locate entries that reference it (via `Motivated by`, `Prevents`, `Motivated`) and re-evaluate them:

```
The following entry was flagged: [paste flagged entry + classification]
These entries reference it: [paste referencing entries]

For EACH referencing entry, classify: UNCHANGED | CONTRADICTED | NARROWED | STALE.
Reason: the underlying motivation/prevention target shifted — does the referencing entry still hold?
```

This pass is small (only entries with live cross-refs to a flagged target) and catches the contradictions the dimensional split misses.

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

Spawn one subagent with ONLY the new domain file as context:

```
You are planning concrete changes in this domain using ONLY the knowledge file below. You have no other context — no access to the codebase, git, or other files.

Tasks:
- <eval question 1>
- <eval question 2>
- ...
- Plan how you would implement: <past feature title 1>
- Plan how you would implement: <past feature title 2>

For EACH task:
1. Produce a brief plan (3-5 bullets) using only information from the file.
2. List every piece of information you would need to act correctly but cannot find in the file. Each gap is a concrete unanswered question.
3. Rate: green (no gaps), yellow (minor gaps, task achievable), red (critical gaps, task blocked).

Knowledge file:
[paste full domain file]
```

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

Distill generalizable planning lessons from this feature's execution signals. Output: `planwise/knowledge/_lessons.md` — a separate artifact consumed only by `/plan` and `/brief` (leading `_` sorts it apart from domain files and keeps it out of the domain-concept grep path). Lessons are hypotheses; they strengthen through confirmation and graduate into domain knowledge when proven.

This phase reads Phase 2 material through a planning-defect lens. Never duplicate entries across `_lessons.md` and the domain file.

### Step 1: Collect convergence signals

Tag each finding with its signal class:

- **scope-miss** — sub-features added after the plan was approved.
- **risk-miss** — bug sub-features filed during implementation.
- **approach-wrong** — `jj op log` abandons or `--patch` shows discarded approaches on the same file/concept.
- **quality-gap** — optimize verdict `stuck`, or UAT failures on untested assumptions.
- **estimation-miss** — sub-features requiring >1 rework cycle (repeated rewrites on same change-id).

### Step 1.5: Score applied lessons (usefulness feedback)

Measure whether lessons retrieved by the *originating plan, task brief, or bug diagnosis* actually prevented the defects they claimed to guard against.

```bash
planwise view $ARGUMENTS
planwise view <sub-feature-id>    # for every sub-feature from Phase 2 Step 1 (any type)
```

Extract the `## Lessons Applied` block from the feature body (populated by `/plan` Phase 1) AND from every sub-feature body that contains one (populated by `/brief` for task sub-features, `/bug` for bug sub-features). Coding and UAT sub-features created by `/plan` do not carry their own block — they inherit from the feature. Union the retrieved lessons across all sources; if a lesson appears in more than one, score once (de-duplicate by title).

If no block is found in any source AND `_lessons.md` has active entries whose `trigger` domain-tag matches this feature's domain → record **contract-miss**: list their titles in Phase 7 as "lessons plausibly unretrieved". Do not score them as failed — usefulness is unknown, not zero.

For each lesson entry in the block:

1. **Look up** the lesson in `planwise/knowledge/_lessons.md` by title. If not found (archived or promoted) → skip silently.
2. **Determine** the claim class from the entry's `class:` field.
3. **Check this run's Step 1 signals.** If the claimed class appears:
   - Applied and defect class still occurred → the lesson did not prevent what it claimed. Bump `failed_applications` by 1.
4. **If the claimed class does NOT appear:**
   - Applied and defect class did not occur → plausibly worked. Bump `successful_applications` by 1.
5. Update `last_seen` to today.

Record per-lesson verdicts for Phase 7. Do not prune yet — Step 4 applies the updated counters.

`successful_applications` is a weak signal (the feature may not have exercised the risk). `failed_applications` is strong.

### Step 2: Cluster and gate

Group signals by root cause. Apply the gate:

- A candidate lesson requires **≥2 signals of different classes** pointing to the same root cause. Single-class or single-signal clusters = normal adaptation, **discard**.
- Reject candidates that restate CLAUDE.md rules, are feature-specific ("remember X in feat-042"), or describe domain truth (belongs in Phase 3 domain file, not here).

Default to discarding. If no candidate survives: "Nothing to save." — skip the remaining steps. Valid and expected outcome.

### Step 3: Read existing lessons and dedupe

```bash
test -f planwise/knowledge/_lessons.md && cat planwise/knowledge/_lessons.md
```

For each candidate that passed the gate:

- Existing active entry has matching `trigger` + semantically equivalent `lesson` → **bump `confirmations`**, append feature id to `evidence`, update `last_seen`. Do not add a new entry.
- Else → stage a new entry for Step 5.

### Step 4: Apply promotion and pruning

**Promote (gated by rewrite review).** Any active entry where `successful_applications >= 3 AND failed_applications == 0` AND whose `trigger` is scoped to a single domain is a promotion candidate. Do NOT promote directly. Spawn a **rewrite reviewer** subagent:

```
Input:
- Original lesson entry: [paste full entry]
- Proposed domain entry: [paste your rewrite as a Decision or Gotcha]
- Target section in domain file: [paste the existing section]

Checks:
1. Does the rewrite preserve the lesson's actionable trigger?
2. Is it in the right section (Decision for design-choice, Gotcha for failure-mode)?
3. Does it duplicate an existing entry in the target section? If yes, merge into the existing entry (preserving both evidence trails) instead of adding.
4. Does it meet the Writing Principles and carry a `source:` field?

Output: approve | revise (with reasons) | reject (with reason).
```

Only approved rewrites land in the domain file and leave `_lessons.md`. Report all outcomes in Phase 7. Promotions remain rare — rewrite review is low ongoing cost.

**Skip rewrite review at Trivial scale** — promotion still applies, but use direct rewrite following Writing Principles (no reviewer subagent).

**Prune — quality-driven (strong signal):** move any entry where `failed_applications > successful_applications` to `## Archive` immediately, regardless of age. Reason: `net failure: F failed / S successful`.

**Prune — age-driven (safety net):** move entries where `confirmations: 1 AND successful_applications == 0 AND failed_applications == 0` and `(current_feature_number - first_evidence_feature_number) >= 10` to `## Archive`. Reason: `untriggered >= 10 features`.

Archived entries are kept for audit but excluded from the `/plan` grep path.

**Size cap:** `## Active` holds at most **40 entries**. If adding new lessons would exceed the cap, consolidate first (merge semantically overlapping entries, preserving higher `confirmations` and unioning `evidence`) or archive lowest-`confirmations` entries.

### Step 5: Write `_lessons.md`

If the file does not exist, create with this header:

```markdown
# Planning Lessons

Hypotheses about how /plan and /brief should approach work in this codebase, distilled from execution signals by /memo Phase 6. Consumed by /plan Phase 1 and /brief Phase 1. Lessons strengthen through confirmation and graduate into domain knowledge when `successful_applications >= 3 AND failed_applications == 0`.

Retrieval: grep -i -B1 -A5 "<keyword-or-domain-tag>" planwise/knowledge/_lessons.md

## Active
```

Entry format under `## Active`:

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

Append `## Archive` at the bottom (same format). Preserve untouched entries.

### Step 6: Quality gate

- Every lesson has a concrete `trigger` (domain tag, file glob, or keyword set).
- Every `lesson` is one sentence, present tense, evergreen.
- Every lesson has a `class`.
- No duplicate of CLAUDE.md rule or Phase 4 domain entry.
- All approved promotions are applied (domain file updated, entry removed from `_lessons.md`) before writing.
- `## Active` section ≤ 40 entries after consolidation.

If zero lessons survive: write nothing; note "Nothing to save." in Phase 7.

## Phase 6.5: Cross-domain reflection (cadence-gated)

Single-feature `/memo` cannot see patterns spanning domains. This phase runs periodically to surface them.

### Cadence gate

Run ONLY when:
- This feature brings the domain's `features:` count to a multiple of 5, OR
- This feature touched >1 domain.

Otherwise skip. Record "skipped (cadence: <reason>)" in Phase 7. Most runs skip.

### Reflection call

One subagent. Input: per-domain frontmatter + section headings + entry titles only (no bodies — bounds context).

```bash
for f in planwise/knowledge/*.md; do
  [[ "$f" == *INDEX.md || "$f" == *_lessons.md ]] && continue
  head -n 10 "$f"                    # frontmatter
  grep -n '^## \|^- \*\*' "$f"       # section headings + entry titles
done
```

Prompt:

```
You are looking for cross-domain consolidation opportunities across the full knowledge base.

Per-domain snapshot (frontmatter + headings + entry titles, no bodies):
[paste the collected output]

Produce:
1. **Recurring patterns** — concepts appearing as separate entries in 3+ domains. Candidate for a global pattern file or shared module. List: pattern name, domains involved, suggested action.
2. **Terminology drift** — the same concept named differently across domains. Candidate for canonicalization. List: variant names, domains, suggested canonical term.
3. **Redundant gotchas** — gotchas with a common root cause across domains, suggesting a cross-cutting concern. List: gotcha titles, domains, suggested consolidation.

Each finding is a PROPOSAL, not an auto-edit. Report findings for Phase 7 — no file changes.
```

### Apply results

Reflection findings go to the Phase 7 report only. No automatic file changes in this phase — cross-domain edits happen in subsequent human-directed work (a follow-up feature, a dedicated consolidation task).

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
