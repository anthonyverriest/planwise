# Implement — Sub-feature execution protocol

This file is read by subagents spawned from `implement.md`. Main thread does NOT read it.

## Sub-feature implementation

You are implementing a single sub-feature inside an isolated git worktree that shares `.git` with the feature workspace. The worktree HEAD is the current feature tip — prior sub-features are already applied.

Steps — execute all in order. Do not skip.

1. **Load the sub-feature body:**
   ```bash
   planwise view <slug>
   ```

2. **Implement** the Requirements, Edge Cases, Constraints, and Implementation Recipe.
   - Modify ONLY files listed in the recipe's Files & Patterns section.
   - Always Read a file immediately before editing it. Use exact content from the Read output as `old_string`.
   - Match existing patterns. Follow the rules from the Rules input. No scope creep, no drive-by refactors.

3. **Validate:** run the recipe's Validation command.

4. **Test:** write unit/integration tests covering the Requirements and Edge Cases.

5. **Verify Acceptance Criteria** before committing.

6. **Commit:**
   ```bash
   git checkout -b sub/<slug>
   git add <specific-files>
   git commit -m "<type>: <description> (#<slug>)"
   ```
   Commit types: `feat`, `fix`, `ref`, `docs`, `chore`, `style`. Imperative mood.
   Reserved prefixes — do NOT emit: `test:` (owned by /test), `optimize:` (owned by /optimize).

7. **Report** per § **Return contract**.

## Return contract

Return exactly one of:

- **DONE** — implemented cleanly. Include: files changed, test evidence (command + pass/fail line).
- **DONE_WITH_CONCERNS** — implemented but something feels wrong. Describe what. Prefer this over silent guessing.
- **BLOCKED** — codebase doesn't match the recipe. Describe the discrepancy; do not force an implementation.
- **REPLAN** — the recipe's architectural assumption is wrong. Describe actual state + suggested fix.

BLOCKED and REPLAN contribute no commits. DONE and DONE_WITH_CONCERNS must leave a `sub/<slug>` branch.

## Bug label branch

If the sub-feature has the `bug` label: trace the bad value to its origin. Fix at the root cause, not the symptom. After 3 failed fix attempts, stop patching and report findings as BLOCKED — do not try a 4th.
