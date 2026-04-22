# Python extensions for planwise workflows

Two deterministic subcommands that replace LLM-driven checklist work in
`/memo` and externalize state in `/optimize`. Scope is closed: anything
not listed here is explicitly deferred.

## Principles

- Python replaces LLM work **only** where the task is deterministic and
  the failure mode is "reject, never assert completeness."
- Each subcommand ships with tests before it is wired into a skill.
  Agents will trust its output; a silent miss is a correctness
  regression, not a nit.
- Output is JSON on stdout; human-readable text is a render of the JSON.
- Schemas are defined as Pydantic v2 models and are authoritative —
  documentation mirrors the models, not the reverse.

## 1. `pw kb verify` — deterministic KB validation

Replaces the mechanical checklist in `memo.md` Phase 4 Step 5 (lines
398-405) and the dangling-reference hard-fail in Phase 5.5 Step 2
(line 534). Does **not** replace Phase 3.5 — that is semantic staleness
("underlying motivation shifted") and requires LLM judgment.

Lives at `src/planwise/commands/kb.py` as a new `kb` group with a
`verify` subcommand. Distinct from the existing planning-data `pw verify`
(`src/planwise/commands/verify.py`).

### KB schema (target of these checks)

Per `memo.md`:

- `planwise/knowledge/<domain>.md` — narrative entries (human-facing).
- `planwise/knowledge/<domain>.jsonl` — typed records, one per line.
  Phase 5.5 emits this from the `.md`; it is the canonical machine
  form.
- `planwise/knowledge/INDEX.md` — grep-optimized domain map.
- `planwise/knowledge/_lessons.md` — planning lessons (separate
  corpus; not verified here).

The JSONL line shape (from `memo.md:522`) is captured as a Pydantic v2
`KBEntry` model:

```python
class KBEntry(BaseModel):
    id: str            # "<domain>/<section>/<title-slug>"
    domain: str
    section: str
    title: str
    body: str
    critical: bool
    refs: list[str]    # resolved entry ids (target of bidirectional check)
    source: str        # "<sha-short>|<issue-id>"
    updated: date
```

`refs` is the resolved form of the markdown cross-refs (`Motivated by:`,
`Prevents:`, `Motivated:`). Phase 5.5 does the resolution; `kb verify`
treats `refs` as ground truth.

### Checks

All checks run against the `.jsonl` (canonical), not the `.md`. Rules
and their evidence in memo.md:

| Rule                  | Logic                                                                                 | Evidence            |
|-----------------------|---------------------------------------------------------------------------------------|---------------------|
| `jsonl_schema`        | Each line parses under `KBEntry`                                                      | memo.md:522         |
| `source_present`      | `entry.source` is non-empty                                                           | memo.md:338, 403    |
| `critical_ratio`      | Entries with `critical: true` are `< 20%` of the domain                               | memo.md:32, 405     |
| `temporal_language`   | Regex `\b(recently|new|improved|updated|currently|now|lately)\b` in `entry.body`      | memo.md:26          |
| `duplicate_titles`    | Normalized `title` collision within a domain                                          | writing principles  |
| `stale_file_ref`      | Every `@<path>` token in `entry.body` resolves to an existing file on disk            | memo.md:199         |
| `bidirectional_links` | For every id in `entry.refs`, the target entry exists in the JSONL                    | memo.md:534         |

Scope of `stale_file_ref`:
- Matches only the `@<path>` form used for pattern locations in
  memo.md:199. Does not attempt symbol resolution — no `::symbol`
  syntax exists in the KB.
- Path is checked relative to repo root. When the token can't be
  unambiguously parsed as a path, the rule skips (no guess).

Bidirectional check is pure id set-membership over the JSONL.
Reciprocal-direction semantics (`Motivated by` ↔ `Motivated`) are
already flattened into `refs` by Phase 5.5, so this check is symmetric
by construction — if A references B but B does not reference A, both
`refs` lists reveal it.

### CLI

```
pw kb verify [<domain>] [--format json|text]
```

- No `<domain>` → verify all domains under `planwise/knowledge/`.
- No `--fix` flag: every violation here requires a content decision
  the LLM should make. Auto-repair would mask real drift.
- Exit codes: `0` clean, `1` violations found, `2` usage error.

### Output (JSON)

```json
{
  "domains_checked": ["planning"],
  "violations": [
    {"rule": "temporal_language", "entry_id": "planning/decisions/webhook-retry",
     "file": "planwise/knowledge/planning.jsonl", "line": 42, "match": "recently"},
    {"rule": "stale_file_ref", "entry_id": "planning/patterns/idempotency-keys",
     "file": "planwise/knowledge/planning.jsonl", "line": 7,
     "ref": "src/payments/old.py"},
    {"rule": "bidirectional_links", "entry_id": "planning/decisions/retry-policy",
     "file": "planwise/knowledge/planning.jsonl", "line": 12,
     "dangling_ref": "planning/constraints/missing-id"}
  ],
  "stats": {"entries": 142, "critical_count": 18, "critical_pct": 12.7}
}
```

### Skill integration

`/memo` workflow replaces the manual checklists with:

- **Phase 4 Step 5:** `pw kb verify <domain> --format json`. Exit `0`
  → phase passes. Exit `1` → surface violations; LLM fixes content
  and re-runs until clean.
- **Phase 5.5 Step 2:** same command. The `bidirectional_links` rule
  is the hard-fail contract described at `memo.md:534`; any dangling
  ref returns control to Phase 4 Step 2 per the existing workflow.

Exit `2` (usage error) halts with stderr surfaced — never silently
passes.

## 2. `pw ledger` — append-only action log for `/optimize`

Externalizes the two ledgers `/optimize` already maintains:

- **Action ledger** (`optimize.md:143`) — records every auto-fix and
  proposal across iterations. Shape:
  `{id, file, region, action, rationale, stage, outcome, affected_files}`.
- **Challenge ledger** (`optimize.md:177`) — records critiques and
  resolutions across discovery cycles within a single iteration.

Today both live in agent context. Moving them to disk lets iteration 2+
query the ledger directly (avoiding redundant work, per `optimize.md:397`)
and survives crashes.

Lives at `src/planwise/commands/ledger.py`.

### Storage

Per optimize run, keyed by run-id:

- `.planwise/ledger/<run-id>/actions.jsonl` — one line per action entry.
- `.planwise/ledger/<run-id>/challenges.jsonl` — one line per challenge
  entry, with `iteration: int` so a single file covers all iterations.
- `.planwise/ledger/<run-id>/meta.json` — `{run_id, target, started_at}`.

JSONL + append-only matches the shape of the data (entries accrete,
never mutate) and makes concurrent appenders trivial to reason about.

### Schemas

```python
class ActionEntry(BaseModel):
    id: str
    file: str
    region: str                    # line range or section anchor
    action: str                    # short verb: "rename", "extract", etc.
    rationale: str
    stage: Literal["auto_fix", "proposal"]   # optimize.md Phase 4 vs 5
    outcome: Literal["committed", "reverted", "skipped"]
    affected_files: list[str]
    timestamp: datetime

class ChallengeEntry(BaseModel):
    iteration: int
    critique: str
    resolution: Literal["accepted", "rejected", "deferred"]
    rationale: str
    timestamp: datetime
```

### Atomicity and concurrency

- JSONL append: open `O_APPEND`, write a single `json.dumps(...) + "\n"`
  in one `write()` call. POSIX guarantees atomicity for writes under
  `PIPE_BUF` (4096 bytes) on `O_APPEND` files. Entries are well under
  that budget.
- `meta.json` write: serialize to `meta.json.tmp`, `fsync`,
  `os.replace()`. No in-place edit.
- Readers tolerate partial trailing lines (skip + warn) — the
  atomicity contract covers full writes but not process crashes
  mid-syscall on non-POSIX filesystems.

### CLI

```
pw ledger new <target>                             # create run dir, print run-id
pw ledger append actions <run-id> --json <payload> # ActionEntry JSON on stdin or --json
pw ledger append challenges <run-id> --json <payload>
pw ledger query actions <run-id> [--file <path>] [--outcome <outcome>] [--stage <stage>]
pw ledger query challenges <run-id> [--iteration <n>]
pw ledger list [--format json|text]                # list runs
pw ledger show <run-id>                            # meta + counts
```

All queries emit JSON (array of entries). Exit codes: `0` success, `1`
not-found, `2` usage / schema error.

### Skill integration

`/optimize` workflow changes:

- **Phase 2 Baseline:** `RUN_ID=$(pw ledger new "$TARGET")`. Store in
  conversation context as before — the run-id is the only piece of
  state the LLM has to carry.
- **Phase 4 and 5 (execute):** after each commit/revert/skip decision,
  `pw ledger append actions "$RUN_ID" --json '<entry>'`. Replaces the
  in-context `ledger.append(...)` pseudocode.
- **Phase 3 iteration 2+:** the "Ledger so far: [ledger entries for
  files in scope]" prompt at `optimize.md:193` is sourced from
  `pw ledger query actions "$RUN_ID" --file <file>` instead of being
  reconstructed from context.
- **Challenge loop:** each critique/resolution is
  `pw ledger append challenges "$RUN_ID" --json '<entry>'`. Phase 3.5
  contradiction detection (`optimize.md:287`) queries
  `pw ledger query challenges "$RUN_ID" --iteration <n>`.

This is a direct 1:1 replacement of data structures already specified
in `optimize.md` — no new concepts.

## Tests

Both commands ship with `pytest` coverage before being wired into
skills.

- **`kb verify` — golden-file tests.** `tests/kb_verify/fixtures/`
  holds synthetic `.jsonl` files: one clean baseline and one targeted
  "bad" fixture per rule. Each test asserts the exact violation list
  on stdout JSON. Adding a rule means adding a fixture.
- **`ledger` — schema + concurrency tests.** Parametrized tests cover
  `ActionEntry`/`ChallengeEntry` validation (valid + rejected shapes)
  and `query` filter combinations. A concurrency test spawns N
  processes appending simultaneously and asserts every line is a
  well-formed JSON entry (POSIX `O_APPEND` atomicity contract).
- **Integration smoke.** One end-to-end test per command invokes the
  CLI as a subprocess against a temp dir — catches packaging /
  entry-point regressions.

## Build order

1. `KBEntry`, `ActionEntry`, `ChallengeEntry` Pydantic models + test
   fixtures. ~0.5 day.
2. `pw kb verify` — rules + golden-file tests. ~1 day.
3. `pw ledger` — append + query + concurrency tests. ~0.5 day.
4. Wire `/memo` Phase 4 / 5.5 and `/optimize` Phase 2-5 to the new
   commands. ~0.5 day.

Total: ~2.5 days.

## Deferred (not building)

- `pw recon` (multi-language AST): silent-miss failure mode, high
  maintenance.
- `pw impact`: grep suffices.
- `pw feature classify`: too thin to justify a subcommand.
- Semantic staleness detection (memo.md Phase 3.5): not deterministic;
  belongs to the LLM.
