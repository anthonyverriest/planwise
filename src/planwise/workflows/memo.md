---
description: "Distill a completed feature into the project knowledge base"
---

# Memo — Knowledge Base Update

Distill a completed feature's learnings into the project knowledge base. Runs after a feature is done. The output is a domain-scoped knowledge file in `planwise/knowledge/` that serves both humans and agents as the current truth about that domain.

The knowledge base is a living artifact — refactored like code, not archived like documents. Each file must pass the **cold start test**: an agent or developer reading only this file can act correctly in the domain without chasing other sources.

## Target: Feature $ARGUMENTS

## Writing principles

Every entry in the knowledge base serves two audiences simultaneously: a developer scanning for context and an agent consuming it as prompt context. These principles govern all writing in Phases 3-4.

**Density without compression.** Every sentence must carry information. No filler, no hedging, no "it should be noted that." But don't sacrifice clarity for brevity — a decision that takes 4 lines to explain properly is better than a 1-line entry that requires the reader to guess the rationale.

**Evergreen language.** Write in present tense about current state. No temporal references ("recently", "in the last sprint", "after the refactor"), no feature-specific framing ("this feature introduced"), no version numbers that will go stale. The entry describes what IS, not what CHANGED.

**Self-contained entries.** Each bullet must stand alone. A reader should never need to read another entry, another file, or the git history to understand what an entry says and why it matters. Include the "why" inline — don't point elsewhere for it.

**Concrete over abstract.** Name specific files, functions, types, error messages. "The payment webhook handler validates idempotency keys" beats "The system ensures idempotent processing." If an entry could apply to any codebase, it's too abstract.

**Signal salience.** Mark load-bearing entries `[critical]` — these are decisions, constraints, or gotchas where getting it wrong causes a production incident, data loss, or security vulnerability. Most entries are unmarked (normal salience). Use `[critical]` sparingly — if more than ~20% of entries are critical, the signal is diluted.

**Link entries across sections.** When a decision exists because of a constraint, or a pattern exists to avoid a gotcha, say so inline: "Motivated by: *[constraint name]*" or "Prevents: *[gotcha name]*." This turns a flat list into a knowledge graph the reader can traverse.

## Phase 1: Validate readiness

```bash
planwise view $ARGUMENTS --field type
planwise view $ARGUMENTS --field status
```

**Guards:**
- Type must be `feature`. If not → stop: `$ARGUMENTS is not a feature.`
- Status must be `done` or `in-review`. If `in-review`, warn: `Feature $ARGUMENTS is in-review, not done. Proceeding — knowledge may be incomplete.` Any other status → stop: `Feature $ARGUMENTS is not complete (status: <status>). Finish the feature first.`

## Phase 2: Gather sources

Collect all raw material — both the feature's artifacts and the existing knowledge base state.

### Step 1: Read the feature and all sub-features

```bash
planwise view $ARGUMENTS
planwise list --children-of $ARGUMENTS --type sub-feature
planwise list --children-of $ARGUMENTS --type bug
planwise list --children-of $ARGUMENTS --type uat
```

Read the full body of each sub-feature:
```bash
planwise view <sub-feature-id>
```

Record:
- Feature title, user story, success criteria, scope, assumptions & risks
- Per sub-feature: title, requirements, implementation notes, acceptance criteria, notes
- Bug sub-features: what broke, root cause, fix approach
- UAT: what was tested, what passed/failed

### Step 2: Read git history for the feature branch

Identify the feature branch from the feature or git:
```bash
git branch --list 'feat/*' 'fix/*'
git log dev..HEAD --oneline --stat
```

If the branch has been merged, find the merge and walk the branch history:
```bash
git log --oneline --stat --merges --grep="$ARGUMENTS" dev
```

Extract:
- Commit messages (encode decisions)
- Reverts (encode gotchas)
- Optimize commits (prefixed `optimize:`) — what was fixed/evolved post-implementation

### Step 3: Read optimize and test artifacts

```bash
git log dev..HEAD --oneline --grep="optimize:"
git log dev..HEAD --oneline --grep="test:"
```

Check sub-feature notes for optimize/test reports:
```bash
planwise view <sub-feature-id>
```

Record:
- Optimize verdict (converged/stuck/stopped), iteration count, what was fixed vs remaining
- Test findings: bugs found, crashes, what held up
- Dimensions that scored well vs poorly

### Step 4: Identify target domain(s) and read existing knowledge

Determine which domain(s) this feature touches. A domain maps to a bounded context or major subsystem (e.g., `auth`, `payments`, `ingestion`). Most features touch one domain; some touch two. More than two suggests the feature was too broad — pick the primary.

```bash
ls planwise/knowledge/
```

If a knowledge file already exists for the target domain, read it in full — subagents need current state to merge against.

```bash
cat planwise/knowledge/<domain>.md
```

## Phase 3: Distill and merge

Launch **3 subagents in one message** — each analyzes the gathered material through a different lens. If an existing knowledge file was found, each subagent receives it alongside the feature material and produces **merged** output.

Every subagent receives the Writing Principles (Phase 0) as part of its prompt. Every entry must follow these principles — reject subagent output that violates them.

### Merge protocol

Each subagent follows the same merge logic when existing knowledge is present:

1. **Detect contradictions.** For each existing entry, compare against the feature's evidence. If the feature contradicts an existing entry (different approach chosen, constraint relaxed, gotcha resolved), flag it explicitly: `[SUPERSEDED]` with a one-line reason.
2. **Keep** entries that remain valid and untouched by this feature.
3. **Update** entries where this feature adds nuance, changes scope, or provides new evidence. Rewrite the entry — don't append a note.
4. **Remove** entries the feature made obsolete (the old version lives in git history). List removals in the subagent output so the report can track them.
5. **Add** new entries from this feature.

When in doubt about whether an existing entry is still valid, keep it and flag: `[VERIFY]` — Phase 4 resolves these.

### Subagent 1: Architecture, Decisions & Patterns

```
You are writing for a project knowledge base that serves both human developers and AI agents.
Follow these writing principles strictly:
- Density without compression: every sentence carries information, no filler, but don't sacrifice clarity for brevity
- Evergreen language: present tense, no temporal references, no feature-specific framing
- Self-contained entries: each entry stands alone with its rationale inline
- Concrete over abstract: name files, functions, types — not vague system descriptions
- Mark load-bearing entries [critical] (production incidents, data loss, security if wrong)
- Link to other sections when a decision is motivated by a constraint or prevents a gotcha

Feature: [title, user story, scope]
Sub-issues: [titles + implementation notes for each]
Git log: [commit messages, file change summary]
Bug fixes: [what broke and why]
Existing knowledge (if any): [full content of current domain file's 1. Architecture, 2. Decisions, and 3. Patterns sections]

Follow the merge protocol: detect contradictions → keep → update → remove → add.
List any [SUPERSEDED] or [VERIFY] flags with reasons.

Produce merged output for three sections:

## 1. Architecture
How this domain works now — the mental model a developer or agent needs before touching this code. Structure as:
- One paragraph: what the domain does and how data flows through it
- Key components: name each with its file path and responsibility (one line each)
- Integration points: how this domain connects to other domains at the code level

Write for someone who has never seen this codebase. After reading this section, they should know where to look and what each piece does.

Example of a good Architecture section:
> The billing domain processes subscription changes and generates invoices. Events flow from the subscription service (`src/billing/events.py`) through the invoice generator (`src/billing/invoice.py`) to the payment gateway adapter (`src/billing/gateway.py`).
>
> - **SubscriptionEngine** (`src/billing/engine.py`) — orchestrates plan changes, proration, and trial logic
> - **InvoiceGenerator** (`src/billing/invoice.py`) — computes line items from subscription deltas
> - **GatewayAdapter** (`src/billing/gateway.py`) — abstracts Stripe/Braintree behind a common interface
>
> Integration: receives `PlanChanged` events from the subscription domain; emits `InvoiceCreated` events consumed by the notification domain.

## 2. Decisions
Why things are the way they are. Each entry explains what was chosen, what was rejected, and why — with enough context that a reader can evaluate whether the decision still holds.

Entry format:
- **[Decision title]** — [What was chosen] over [what was rejected]. [Rationale: the specific constraint, requirement, or tradeoff that drove this choice]. [Consequence: what this means for future work in this domain]. Motivated by: *[constraint or gotcha name, if applicable]*.

Example of a good decision entry:
> - **Gateway abstraction over direct Stripe SDK** — The payment gateway uses an adapter interface (`GatewayPort`) rather than calling Stripe directly. The team evaluated direct SDK usage but chose abstraction because the contract requires supporting Braintree for EU customers by Q3. The adapter adds one layer of indirection but isolates all payment logic from provider-specific types. Motivated by: *multi-provider constraint*.

Example of a bad decision entry (don't write like this):
> - **Used adapter pattern** — Chose adapter over direct calls for flexibility.

Only include decisions a future developer would benefit from knowing. Skip obvious or framework-default choices.

## 3. Patterns
Reusable approaches established or confirmed in this domain. Each entry describes when and why to apply the pattern, not just what it is.

Entry format:
- **[Pattern name]** — [What the pattern is and where it lives: @file_path]. [When to use: the trigger condition]. [How it works: enough detail to apply it correctly]. Prevents: *[gotcha name, if applicable]*.

Example of a good pattern entry:
> - **Idempotent webhook processing** — Every webhook handler in `src/billing/webhooks/` checks `IdempotencyStore.seen(event_id)` before processing. Apply this pattern to any new webhook endpoint. The store uses a 72-hour TTL Redis key — events replayed after 72 hours are reprocessed (acceptable per Stripe's replay semantics). Prevents: *duplicate invoice generation*.

Only include patterns not already documented in CLAUDE.md or project guidelines.
```

### Subagent 2: Gotchas & Constraints

```
You are writing for a project knowledge base that serves both human developers and AI agents.
Follow these writing principles strictly:
- Density without compression: every sentence carries information, no filler, but don't sacrifice clarity for brevity
- Evergreen language: present tense, no temporal references, no feature-specific framing
- Self-contained entries: each entry stands alone with its rationale inline
- Concrete over abstract: name files, functions, types, error messages — not vague descriptions
- Mark load-bearing entries [critical] (production incidents, data loss, security if wrong)
- Link to other sections when a gotcha motivates a decision or pattern

Feature: [title, scope, assumptions & risks from plan]
Sub-issues: [titles + requirements]
Bug fixes: [full bug descriptions and fixes]
Optimize results: [what was fixed, what was evolved, remaining items]
Test results: [bugs found, crashes, what held up]
Git history: [reverts, multiple attempts at same file, optimize fix commits]
Existing knowledge (if any): [full content of current domain file's 4. Gotchas and 5. Constraints sections]

Follow the merge protocol: detect contradictions → keep → update → remove → add.
List any [SUPERSEDED] or [VERIFY] flags with reasons.

Produce merged output for two sections:

## 4. Gotchas
Things that will bite you in this domain — surprises, non-obvious failure modes, common mistakes. Prioritize gotchas that would trap a future developer working in this domain.

Entry format:
- **[Gotcha title]** — [What happens: the observable symptom]. [Why it happens: root cause at the code level]. [How to avoid: specific prevention, not generic advice]. Motivated: *[decision name, if this gotcha exists because of a design choice]*.

Example of a good gotcha entry:
> - **Webhook signature validation fails silently on replays** — Stripe replays use the original timestamp, but the signature validator in `src/billing/webhooks/verify.py` rejects timestamps older than 5 minutes. The handler returns 200 (to prevent Stripe retry storms) but drops the event. Check CloudWatch for `webhook.signature.stale` metrics if invoices appear missing. How to avoid: set `STRIPE_WEBHOOK_TOLERANCE=300` in env to match the replay window.

Example of a bad gotcha entry (don't write like this):
> - **Webhook issues** — Sometimes webhooks fail. Make sure to handle errors properly.

For each existing gotcha, check: did this feature fix the root cause? If yes, remove the gotcha — the fix is in the code now. Don't keep warnings about problems that no longer exist.

## 5. Constraints
Invariants, performance bounds, security boundaries, and hard requirements. These are the rules that cannot be broken without consequences. Only include constraints backed by evidence from optimize/test results, explicit requirements, or production incidents.

Entry format:
- `[critical]` **[Constraint title]** — [What the constraint is: specific, measurable where possible]. [Why it exists: the requirement, regulation, or failure that established it]. [What breaks: concrete consequence of violation].

Example of a good constraint entry:
> - `[critical]` **Invoice generation latency < 500ms p99** — The invoice generation path from `SubscriptionChanged` event to `InvoiceCreated` event must complete within 500ms at p99. The downstream notification service has a 1s timeout on invoice events — exceeding 500ms causes notification delivery failures that surface as "missing receipt" support tickets. Measured via `invoice.generation.duration` metric in Datadog.

Example of a bad constraint entry (don't write like this):
> - **Must be fast** — Invoice generation should be performant.
```

### Subagent 3: Context & Connections

```
You are writing for a project knowledge base that serves both human developers and AI agents.
Follow these writing principles strictly:
- Density without compression: every sentence carries information, no filler
- Evergreen language: present tense, no temporal references, no feature-specific framing
- Concrete over abstract: name specific modules, interfaces, data flows

Feature: [title, user story, success criteria, scope]
Sub-issues: [titles + dependencies]
Files changed: [list from git]
Existing knowledge (if any): [full content of current domain file's preamble and 6. Connections section]

Follow the merge protocol: detect contradictions → keep → update → remove → add.

Produce merged output for two parts:

### Preamble
2-3 sentences describing what this domain is, its role in the system, and the core abstraction it provides. Not what any feature did — what this domain IS. After reading the preamble, a developer should know whether their problem lives in this domain or elsewhere.

Example of a good preamble:
> The billing domain owns the lifecycle of subscriptions, invoices, and payment processing. It translates business events (plan changes, trials, cancellations) into financial records and coordinates with external payment providers through an adapter interface. All monetary calculations use `Decimal` types — no floats touch this domain.

Example of a bad preamble (don't write like this):
> This domain handles billing stuff. It was created to manage payments.

If existing preamble is present, update only if this feature changed the domain's scope, role, or core abstraction.

## 6. Connections
Map the domain's relationships to help `/plan` sessions understand ripple effects and blast radius.

- **Depends on:** [Domains or services this domain calls, imports from, or requires — name the interface or contract]
- **Shared types:** [Types, schemas, or events that cross domain boundaries — only include if misusing the type causes a bug that grep alone wouldn't reveal]
- **Deferred work:** [Anything explicitly deferred or left as out-of-scope — remove items from prior features that have since been completed. Only keep items that are still relevant and unaddressed]

Consumers are discoverable via `grep` and the list goes stale immediately. The knowledge base tracks what this domain needs, not who uses it.

If existing connections are present, merge: add newly discovered connections, remove ones that are no longer accurate, keep the rest. Every connection must name a specific interface, type, or contract — no vague "interacts with the frontend."
```

## Phase 3.5: Contradiction sweep

**Skip this phase if no existing knowledge file was found — there is nothing to contradict.**

The Phase 3 subagents focus on their lens (architecture, gotchas, connections) and catch obvious contradictions. But they can miss entries that are *indirectly* invalidated — a constraint that was silently relaxed, a gotcha whose root cause was fixed as a side effect, a decision whose rationale no longer holds because a dependency changed.

The contradiction sweep is a dedicated verification pass over every entry the subagents **kept unchanged**. It has one job: find what the subagents missed.

### Step 1: Build the kept-entries list

From each subagent's output, collect every entry that was carried forward unchanged from the existing knowledge file. These are entries the subagents judged as "still valid" — the sweep challenges that judgment.

Exclude entries the subagents already marked `[SUPERSEDED]`, `[VERIFY]`, updated, or removed — those are already handled.

### Step 2: Run the sweep by dimension

Each knowledge section can only be contradicted by specific types of feature evidence. Split the sweep by dimension so each call has a focused lens and a bounded context. Launch sweep calls **in parallel** — they are independent.

Skip any dimension that has zero kept entries.

#### Dimension: Architecture & Decisions

```
You are a contradiction detector. Your ONLY job is to find Architecture and Decision entries that are no longer accurate given new evidence.

## Evidence (scope: structural changes)
- Feature scope and assumptions & risks
- Sub-issue implementation notes
- Commit messages (encode decisions made during implementation)
- Files changed (show what moved, was added, or removed)

[Paste only the above from Phase 2]

## Entries to verify
[Paste kept-unchanged 1. Architecture content and 2. Decision entries]

For EACH entry, classify:
- UNCHANGED — The feature has no bearing on this entry.
- CONTRADICTED — The feature chose a different approach, replaced a component, or reversed this decision. [Evidence: name the sub-feature, commit, or scope change that contradicts it. State the new truth.]
- NARROWED — The decision still holds but the feature added exceptions or shifted its boundaries. [Evidence: what changed and how the entry should be updated.]
- STALE — The entry references files, types, or components that the feature renamed, moved, or removed. [Evidence: what moved or changed.]

Rules:
- Default to UNCHANGED — only flag what the evidence shows.
- Be specific: name the exact sub-feature or commit.
```

#### Dimension: Patterns

```
You are a contradiction detector. Your ONLY job is to find Pattern entries that are no longer accurate given new evidence.

## Evidence (scope: implementation changes)
- Sub-issue implementation notes
- Files changed with diffs summary
- Commit messages

[Paste only the above from Phase 2]

## Entries to verify
[Paste kept-unchanged 3. Pattern entries]

For EACH entry, classify:
- UNCHANGED — The pattern is still applied as described.
- CONTRADICTED — The feature introduced a different pattern for the same concern, or the code no longer follows this pattern. [Evidence: name the sub-feature or commit. State what replaced it.]
- NARROWED — The pattern still applies but its scope, trigger condition, or mechanism changed. [Evidence: what changed.]
- STALE — The entry references files or functions that were renamed, moved, or removed. [Evidence: what moved.]

Rules:
- Default to UNCHANGED — only flag what the evidence shows.
- Be specific: name the exact sub-feature or commit.
```

#### Dimension: Gotchas

```
You are a contradiction detector. Your ONLY job is to find Gotcha entries that are no longer accurate given new evidence.

## Evidence (scope: fixes and quality results)
- Bug sub-features: what broke, root cause, fix approach
- Optimize results: what was fixed, what was evolved
- Test results: what passed, what failed
- Reverts and multi-attempt commits from git history

[Paste only the above from Phase 2]

## Entries to verify
[Paste kept-unchanged 4. Gotcha entries]

For EACH entry, classify:
- UNCHANGED — The gotcha still exists as described.
- CONTRADICTED — The feature fixed the root cause of this gotcha. The problem no longer exists. [Evidence: name the bug fix, optimize result, or commit that resolved it.]
- NARROWED — The gotcha still exists but the feature reduced its scope, added a safeguard, or changed the symptoms. [Evidence: what changed.]
- STALE — The entry references files, error messages, or behaviors that the feature modified. [Evidence: what moved or changed.]

Rules:
- Default to UNCHANGED — only flag what the evidence shows.
- Be specific: name the exact bug fix or optimize result.
```

#### Dimension: Constraints

```
You are a contradiction detector. Your ONLY job is to find Constraint entries that are no longer accurate given new evidence.

## Evidence (scope: requirements and measurements)
- Feature success criteria and assumptions & risks
- Test results: performance data, security findings, what held up
- Optimize results: what was measured, what improved or degraded
- Bug sub-features involving constraint violations

[Paste only the above from Phase 2]

## Entries to verify
[Paste kept-unchanged 5. Constraint entries]

For EACH entry, classify:
- UNCHANGED — The constraint still holds as described.
- CONTRADICTED — The feature relaxed, tightened, or removed this constraint. [Evidence: name the success criterion, test result, or decision that changed it. State the new boundary.]
- NARROWED — The constraint still exists but the feature changed its threshold, scope, or measurement method. [Evidence: what changed.]
- STALE — The entry references metrics, tools, or thresholds that the feature replaced. [Evidence: what changed.]

Rules:
- Default to UNCHANGED — only flag what the evidence shows.
- Be specific: name the exact test result or success criterion.
```

### Step 3: Apply sweep results

For each non-UNCHANGED result:
- **CONTRADICTED**: rewrite the entry with the new truth, or remove it if the concept no longer applies. The subagent provided the evidence — use it to write the corrected entry.
- **NARROWED**: update the entry to reflect the new scope or exceptions. Preserve what's still accurate, adjust what changed.
- **STALE**: verify the referenced code still exists (Glob/Grep). If it moved, update the reference. If it was removed, remove the entry.

Fold these corrections into the subagent outputs before composing the final document.

## Phase 4: Compose and challenge

Merge the three subagent outputs (with contradiction sweep corrections applied) into a single document, then stress-test it.

### Step 1: Resolve flags

Review all remaining `[SUPERSEDED]` and `[VERIFY]` flags from subagent output:
- `[SUPERSEDED]`: remove the old entry. The subagent already wrote the replacement or determined the entry is obsolete.
- `[VERIFY]`: investigate — read the relevant code or issue to determine if the entry is still valid. Keep, update, or remove based on findings.

Do NOT leave flags in the final document.

### Step 2: Cross-reference entries

Check for internal consistency across sections:
- Every `Motivated by:` reference in Decisions points to a real Constraint or Gotcha entry
- Every `Prevents:` reference in Patterns points to a real Gotcha entry
- Every `Motivated:` reference in Gotchas points to a real Decision entry
- Connections list types/interfaces that actually exist in Decisions or Architecture

Fix broken references: either add the missing entry or remove the dangling reference.

### Step 3: Determine domain name and tags

**Domain name:** lowercase, hyphenated slug matching the bounded context (e.g., `auth`, `event-ingestion`, `billing`).

**Tags** (3-6): generated from key technologies, patterns, or cross-cutting concerns used in this domain. Lowercase, hyphenated. No generic tags like `feature` or `code`. Merge with existing tags if updating.

### Step 4: Write or update the knowledge file

File path:
```
planwise/knowledge/<domain>.md
```

```bash
mkdir -p planwise/knowledge
```

Use this template:

```markdown
---
domain: <domain-name>
tags: [<tag1>, <tag2>, <tag3>]
features: [<N>, <N>]
updated: <YYYY-MM-DD>
---

# <Domain Name>

<Preamble from Subagent 3>

## 1. Architecture

<From Subagent 1 — mental model, components, integration points>

## 2. Decisions

<From Subagent 1 — each self-contained with rationale, consequences, and cross-references>

## 3. Patterns

<From Subagent 1 — each with trigger condition, mechanism, and cross-references>

## 4. Gotchas

<From Subagent 2 — each with symptom, root cause, prevention, and cross-references>

## 5. Constraints

<From Subagent 2 — each with measurement, origin, and failure consequence>

## 6. Connections

<From Subagent 3 — depends on, shared types (if non-obvious constraints), deferred work>
```

**Retrieval convention:** Consumers grep for `^## [0-9]` to get a section TOC with line numbers, then read only the needed section by offset. Never `cat` the full file.

If updating an existing file, preserve the `features` list (append the new feature number) and set `updated` to today's date.

### Step 5: Quality gate

Before finalizing, verify the document against these criteria:

**Cold start test:** An agent or developer reading ONLY this file can:
- Understand what the domain does and where the code lives (Architecture)
- Know why things are built the way they are (Decisions)
- Apply established approaches correctly (Patterns)
- Avoid known failure modes (Gotchas)
- Respect hard boundaries (Constraints)
- Understand what other domains are affected by changes here (Connections)

**Entry quality check:**
- Every entry names specific files, functions, types, or error messages — nothing reads like generic advice
- Every Decision includes what was rejected and why — not just what was chosen
- Every Gotcha includes an observable symptom — not just "be careful with X"
- Every Constraint includes a measurable threshold or concrete boundary — not just "must be fast"
- No entry uses temporal language, feature-specific framing, or placeholder language
- `[critical]` markers are used and account for <20% of entries
- All cross-references (`Motivated by`, `Prevents`, `Motivated`) resolve to real entries

**Structural check:**
- No duplicate entries covering the same knowledge from different angles
- No orphaned entries that reference removed decisions, patterns, or constraints
- Architecture is a navigational map — flow, components, integration points — not documentation
- Preamble is 2-3 sentences — it's a filter, not a summary

If any check fails, fix it before writing the file.

### Split heuristic

Split only when subdomains are independently actionable (e.g., `auth.md` → `auth-oauth.md` + `auth-sessions.md`). A coherent domain that runs long is better than two fragments that fail the cold start test. Each resulting file must pass the cold start test independently. Update the index accordingly.

## Phase 5: Update the index

The index is a grep-optimized domain map. Consumers grep INDEX.md to discover which domain file contains a concept, then grep the domain file for section offsets. The index must contain enough entry titles that a single grep finds the right domain + section.

### Retrieval convention

```bash
# Find which domain: grep INDEX.md for a concept
grep -i "idempotent" planwise/knowledge/INDEX.md

# Read the domain file, or retrieve specific sections by offset:
cat planwise/knowledge/<domain>.md
# or:
grep -n '^## [0-9]' planwise/knowledge/<domain>.md  # section TOC with line numbers
# then read the needed section by offset
```

### If `planwise/knowledge/INDEX.md` does not exist, create it:

```markdown
# Knowledge Base

Living knowledge about each domain in the system. Each file contains the current truth — architecture, decisions, patterns, gotchas, constraints, and connections. Updated by `/memo` after each feature.

Retrieval: `grep -i "<keyword>" planwise/knowledge/INDEX.md` → find domain + section, then read the domain file or `grep -n '^## [0-9]' planwise/knowledge/<domain>.md` for section offsets.

## Domains
```

### Add or update the entry for this domain:

```markdown
- **[<Domain Name>](./<domain>.md)** — <preamble summary> | `<tag1>` `<tag2>` `<tag3>`
  - Decisions: <comma-separated decision titles>
  - Patterns: <comma-separated pattern titles>
  - Gotchas: <comma-separated gotcha titles>
  - Constraints: <comma-separated constraint titles>
```

One block per domain. If the domain already has an entry, update all lines (summary, tags, and entry titles). Maintain alphabetical order by domain name. Entry titles must match the bold titles in the domain file exactly — they are grep targets.

## Phase 6: Report

```
Knowledge base updated for Feature $ARGUMENTS.

Domain:  <domain-name>
File:    planwise/knowledge/<domain>.md
Action:  <created | updated>

Sections:
  Architecture:  <created | updated | unchanged>
  Decisions:     N entries (M new, K updated, J removed) [P critical]
  Patterns:      N entries (M new, K updated, J removed)
  Gotchas:       N entries (M new, K updated, J removed)
  Constraints:   N entries (M new, K updated, J removed) [P critical]
  Connections:   <created | updated | unchanged>

Cross-references: N links between entries
Contradiction sweep: N entries verified, M corrections (list one-line summaries)
Quality gate: all checks passed

Tags: <tag1>, <tag2>, <tag3>

This knowledge is available as context for future /plan sessions.
To browse: grep -n '^## [0-9]' planwise/knowledge/<domain>.md
To search: grep -i "<keyword>" planwise/knowledge/INDEX.md
```
