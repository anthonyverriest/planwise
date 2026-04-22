# Memo — Adversarial reader protocol

This file is read by the subagent spawned from `memo.md` Phase 4.5. Main thread does NOT read it.

## Adversarial reader

You are planning concrete changes in this domain using ONLY the knowledge file provided in your input. You have no other context — no access to the codebase, git, or other files.

Your input will include:
- **Tasks** — a list of eval questions plus 1-2 past-feature hypotheticals to plan.
- **Knowledge file** — the full text of the new `<domain>.md`.

For EACH task:

1. Produce a brief plan (3-5 bullets) using only information from the file.
2. List every piece of information you would need to act correctly but cannot find in the file. Each gap is a concrete unanswered question.
3. Rate:
   - **green** — no gaps.
   - **yellow** — minor gaps, task achievable.
   - **red** — critical gaps, task blocked.

Do not hallucinate or infer content not present in the file. If you find yourself guessing, that is a gap — record it.

## Return contract

For each task:

```
### Task: [title or eval question]
**Plan:**
- bullet 1
- bullet 2
...
**Gaps:**
- gap 1
- gap 2
**Rating:** green | yellow | red
```

At the end, a summary line:

```
SUMMARY: green=N yellow=N red=N
```
