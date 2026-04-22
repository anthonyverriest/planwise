# Memo — Distillation subagent protocols

This file is read by subagents spawned from `memo.md`. Main thread does NOT read it.

Every entry you produce must obey the **Writing Principles** below and the **Merge protocol**. The orchestrator will reject output that violates either.

## Writing principles

- **Density without compression.** Every sentence carries information. No filler, no hedging. Clarity beats brevity — 4 lines with rationale beat 1 line that forces guessing.
- **Evergreen language.** Present tense about current state. No "recently", "in the last sprint", "this feature introduced", version numbers. Describe what IS, not what CHANGED.
- **Self-contained entries.** Each bullet stands alone. Include the "why" inline — never point elsewhere.
- **Concrete over abstract.** Name specific files, functions, types, error messages. If it could apply to any codebase, it's too abstract.
- **Signal salience.** Mark load-bearing entries `[critical]` — decisions, constraints, or gotchas where getting it wrong causes production incident, data loss, or security vulnerability. Keep to <20% of entries.
- **Link entries across sections.** Inline: "Motivated by: *[constraint or gotcha name]*" or "Prevents: *[gotcha name]*". The orchestrator's Phase 5.5 enforces bidirectional integrity — broken references hard-fail.
- **Provenance.** Every new entry carries `source: <commit-sha-short> | <issue-id>`. Entries without a source are rejected.

## Merge protocol

1. **Detect contradictions.** For each existing entry, compare against the feature's evidence. If contradicted (different approach chosen, constraint relaxed, gotcha resolved), flag `[SUPERSEDED]` with a one-line reason.
2. **Keep** entries untouched by this feature.
3. **Update** entries where this feature adds nuance — rewrite, don't append a note. Update `source:` to the newer evidence.
4. **Remove** entries the feature made obsolete (old version lives in git).
5. **Add** new entries. Every new entry must include `source: <sha-short> | <issue-id>`.

When uncertain whether an existing entry is still valid, keep it and flag `[VERIFY]` — Phase 4 resolves these.

## Subagent 1: Architecture, Decisions, Patterns, Rejected

You are writing for a project knowledge base that serves both human developers and AI agents. Follow the Writing Principles strictly.

Your input will include:
- Feature: title, user story, scope
- Sub-issues: titles + implementation notes
- Git log: commit messages + SHAs + file changes
- Bug fixes: what broke and why
- Abandoned / rejected approaches (from jj op log)
- Existing knowledge (if any): full sections 1. Architecture, 2. Decisions, 3. Patterns, 7. Rejected

Follow the merge protocol. List `[SUPERSEDED]` or `[VERIFY]` flags with reasons.

Produce merged output for four sections:

### 1. Architecture
How this domain works — the mental model a reader needs before touching this code.
- One paragraph: what the domain does and how data flows through it.
- Key components: name each with its file path and responsibility.
- Integration points: how this domain connects to others at the code level.

### 2. Decisions
Why things are the way they are. Entry format:
- **[Decision title]** — [What was chosen] over [what was rejected]. [Rationale: specific constraint or tradeoff]. [Consequence for future work]. Motivated by: *[constraint or gotcha name, if applicable]*. source: <sha> | <issue-id>

Only include decisions a future developer would benefit from knowing. Skip framework-default choices.

### 3. Patterns
Reusable approaches established or confirmed. Entry format:
- **[Pattern name]** — [What the pattern is and where it lives: @file_path]. [When to use: trigger condition]. [How it works: enough detail to apply]. Prevents: *[gotcha name, if applicable]*. source: <sha> | <issue-id>

Only include patterns not already in CLAUDE.md or project rulesets.

### 7. Rejected
Approaches considered and deliberately not taken in this domain. Prevents future agents from re-proposing dead ends. Entry format:
- **[Approach title]** — [What was considered]. [Why rejected: the specific constraint, cost, or failure that ruled it out]. [What it would look like if reconsidered: the condition that would flip the decision]. source: <sha> | <issue-id>

Populate from: abandoned approaches in jj op log, reverted commits, decisions' "rejected alternatives", and options explicitly ruled out in scope or assumptions & risks. Skip trivial rejections.

## Subagent 2: Gotchas & Constraints

You are writing for a project knowledge base that serves both human developers and AI agents. Follow the Writing Principles strictly.

Your input will include:
- Feature: title, scope, assumptions & risks
- Sub-issues: titles + requirements
- Bug fixes: full descriptions and fixes
- Optimize results: what was fixed, what was evolved, remaining items
- Test results: bugs found, crashes, what held up
- Git history: reverts, multi-attempt commits, SHAs
- Existing knowledge (if any): full sections 4. Gotchas, 5. Constraints

Follow the merge protocol. List `[SUPERSEDED]` or `[VERIFY]` flags.

### 4. Gotchas
Things that will bite you in this domain. Entry format:
- **[Gotcha title]** — [Observable symptom]. [Root cause at the code level]. [How to avoid: specific prevention]. Motivated: *[decision name, if applicable]*. source: <sha> | <issue-id>

For each existing gotcha: did this feature fix the root cause? If yes, remove — the fix is in the code.

### 5. Constraints
Invariants, performance bounds, security boundaries. Only include constraints backed by evidence (optimize/test results, explicit requirements, production incidents). Entry format:
- `[critical]` **[Constraint title]** — [What the constraint is, measurable]. [Why it exists]. [What breaks on violation]. source: <sha> | <issue-id>

## Subagent 3: Preamble & Connections

You are writing for a project knowledge base that serves both human developers and AI agents. Follow the Writing Principles strictly.

Your input will include:
- Feature: title, user story, success criteria, scope
- Sub-issues: titles + dependencies
- Files changed: list from git
- Existing knowledge (if any): preamble and 6. Connections

Follow the merge protocol.

### Preamble
2-3 sentences describing what this domain is, its role in the system, and the core abstraction it provides. Not what any feature did — what this domain IS. Update only if this feature changed scope, role, or core abstraction.

### 6. Connections
- **Depends on:** [Domains/services this domain calls, imports, or requires — name the interface or contract]
- **Shared types:** [Types, schemas, or events crossing domain boundaries — only if misuse causes a bug grep alone wouldn't catch]
- **Deferred work:** [Items explicitly deferred — remove anything completed by this or prior features]

Consumers are discoverable via grep and go stale immediately; the KB tracks what this domain needs, not who uses it.

## Trivial scale: combined subagent

If your input flags **Trivial scale**, you are the single combined subagent. Produce all three subagents' outputs above (Architecture + Decisions + Patterns + Rejected, Gotchas + Constraints, Preamble + Connections) in one pass. Same Writing Principles, same merge protocol.
