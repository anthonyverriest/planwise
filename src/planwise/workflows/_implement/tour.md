# Implement — Dispatchable protocols

This file is read by subagents spawned from `implement.md`. Main thread does NOT read it.

## Tour writer

Produce a guided walkthrough of the feature's changes, used as the PR body. The tour is a **reading order over the diff**, not a document beside it — it tells the reviewer where to start, what is subtle, what decisions are worth knowing, and what to skip.

### Inputs

The orchestrator hands you a bundle containing:
- Feature slug
- `jj diff --from dev@origin --stat` (file list with change sizes)
- `jj diff --from dev@origin` (full patch)
- Sub-feature bodies (title, requirements, constraints, implementation recipe)
- Commit log `dev@origin..@` (descriptions + SHAs)
- Implementer concerns — bundled `DONE_WITH_CONCERNS` text from sub-feature reports, or `"None"`
- Cross-boundary review findings from Step 4, or `"None"`

Do not fetch additional context. Work from the bundle.

### Stop types

Each stop is one of exactly four types. The type is implicit in the wording — do NOT label stops with headers or tags.

- **Entry** — where a reviewer should start reading. Phrasing: `"start here: <what this file/range does>"`.
- **Subtle** — a load-bearing line or range where getting it wrong breaks something non-obvious. Phrasing: `"load-bearing: <what must remain true>"` or `"without this: <what breaks>"`.
- **Decision** — a choice with a rejected alternative worth knowing. Phrasing: `"chose <X> over <Y> because <specific constraint>"`.
- **Skip** — mechanical files (renames, generated code, straight boilerplate, migration scaffolding) the reviewer can safely skim. Phrasing: `"mechanical, skip unless curious"`.

If the bundled implementer concerns contain a specific file:line, emit that as a Subtle stop with the concern text quoted verbatim (no paraphrasing).

### Hard rules

These are non-negotiable. Violations will be rejected by the main-thread sanity check.

- **≤ 10 stops total.** Cut aggressively. Truncation beats noise.
- **One sentence per stop, ≤ 25 words.** No adjectives like `elegant`, `clean`, `robust`, `simple`, `straightforward`.
- **Every stop cites `path:Lxx` or `path:Lxx-Lyy`.** Skip stops may cite a directory glob (e.g. `migrations/*.sql`).
- **Every cited path must appear in the diff.** Do not cite files the patch does not touch.
- **At least one Skip stop when mechanical files exist.** The skip-sign is required signal, not optional — reviewers must know where not to spend attention.
- **Pedagogical order, not alphabetical.** Entry first. Then stops that build intuition for the subtle/decision stops. Skip-signs last.
- **No stops for framework defaults, formatter output, or pure renames.** If the only content is mechanical, collapse the whole change into one Skip stop.

### Degenerate cases

- **Pure mechanical change** (rename, formatting, generated code only): emit 2 stops — one Entry naming the anchor file, one Skip covering the rest.
- **Single-file fix**: 1-3 stops is allowed and expected. Do not pad.
- **No subtle content, no decisions worth knowing**: emit Entry + Skip only. Do not invent subtlety.

### Output contract

Return exactly this Markdown, nothing else — no preamble, no trailing commentary:

```markdown
## Tour (<N> stops · ~<X> min)

1. `<path>:L<start>-L<end>` — <one sentence>.
2. `<path>:L<line>` — <one sentence>.
3. ...

Closes #<feature-slug>
```

Time estimate: 1 minute per stop for Entry/Subtle/Decision, 0 minutes for Skip. Round to the nearest minute.

### Anti-patterns (rejection triggers)

Do not emit:
- Stops that restate what the diff viewer already shows ("adds a new function called X")
- Adjective-laden stops ("cleanly refactors", "robust handling of")
- Stops pointing at files the patch does not modify
- More than 10 stops
- Stops without `path:Lxx` references
- A tour with zero Skip stops when 3+ mechanical files exist
- Section headers grouping stops by type — the sequence is flat and numbered

### Return shape

Return the Markdown block above. No explanation, no notes, no "here is the tour:" preamble. The orchestrator will use your output verbatim as the PR body.
