# Optimize — Fix & evolution execution protocols

This file is read by subagents spawned from `optimize.md`. Main thread does NOT read it.

**Evaluator lock:** Do NOT modify test files or test fixtures (e.g., `tests/`, `__tests__/`, `*_test.*`, `*.spec.*`, and any test helper/fixture files). If a change breaks tests, the change is wrong — not the tests.

Follow the Rules passed in your input.

## Fix

Fix the findings listed in your input (max 5 per dispatch, single file).

Rules:
- Optimize for best code, not smallest diff. The result should read like it was written correctly from the start — not patched.
- Prefer deletions over additions. Added complexity must justify itself.
- No drive-by refactors.

Steps:
1. State hypothesis: what you expect and why.
2. Read target file + context (imports, callers, related files in the same module).
3. Follow the rules from your input.
4. Fix. If multiple approaches work, pick the one that produces the cleanest result.
5. Self-verify: re-read your diff against the specific finding. For each finding you addressed:
   - Does the diff eliminate the exact issue described at @location? (re-read the changed code — is the problem gone?)
   - Does the fix follow the rules, or did you invent a different approach?
   - Did you change ONLY what's needed, or did scope creep in?
   If any answer is no, revise before reporting.

### Return contract (fix)

```
FIXED: [one-line hypothesis] | Files: [list] | Lines changed: [N]
SKIPPED: [one-line reason] | Finding: #N
PARTIAL: [one-line what remains] | Files: [list]
```

## Evolve

Apply the proposal in your input to the target file(s). The discovery phase already ordered fixes before proposals — read the post-fix code and self-correct if the proposal no longer applies.

Rules:
- The change must be a clear improvement — simpler, faster, safer, or more accessible.
- If after reading the code you realize the proposal won't improve things, report SKIP.

Steps:
1. Read target file + context.
2. Follow the rules from your input.
3. Apply the change.

### Return contract (evolve)

```
APPLIED: [one-line what changed] | Files: [list]
SKIP: [one-line why proposal doesn't hold up]
```
