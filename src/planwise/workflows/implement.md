---
description: "Implement all coding sub-features for an feature (automated mode)"
---

# Implement Full Feature (Automated)

Implement all coding sub-features for an feature following its dependency graph.

## Target: Feature $ARGUMENTS

## Worktree detection

Before starting, detect whether you are running inside a git worktree:

```bash
git rev-parse --absolute-git-dir
```

If the output contains `/worktrees/`, you are in a **worktree session** — another feature is being implemented in the main working tree. This is expected during parallel multi-feature execution. In worktree mode:
- You are already on the correct feature branch — skip branch creation (Step 2).
- Other features may be `in-progress` concurrently — this is normal, not a conflict.

## Process

### Step 1: Read the feature

```bash
planwise view $ARGUMENTS
```

**Lock check** — if **this specific feature** is already `in-progress`, stop:
```bash
planwise view $ARGUMENTS --field status
```
If status is `in-progress`, STOP: `Feature $ARGUMENTS is already being implemented. Coordinate before proceeding.`

Other features being `in-progress` is expected during parallel execution — only check **this** feature.

Understand the full scope, the WHAT and WHY. Note the feature title — you will derive the branch name from it.

Move the feature to **in-progress**:

```bash
planwise status $ARGUMENTS in-progress
```

### Step 2: Create or switch to the feature branch

**If in a worktree:** skip this step — you are already on the correct branch.

Check if a feature branch for this feature already exists (from a previous `/implement` run):

```bash
git branch --list 'feat/*' 'fix/*'
```

- **Branch exists:** Switch to it.
  ```bash
  git checkout feat/<topic>
  ```

- **No branch yet:** Create one from `dev`.
  ```bash
  git checkout dev
  git pull --rebase origin dev
  git checkout -b feat/<topic>
  ```

Use a short, descriptive kebab-case topic derived from the feature title. Prefix matches intent: `feat/` for features, `fix/` for fixes (e.g., `feat/club-preferences`, `fix/member-search`).

## Rules

$RULES

### Step 3: List all open coding sub-features

```bash
planwise list --children-of $ARGUMENTS --type sub-feature
```

This returns only coding sub-features (excludes UAT and bug types) with full metadata including labels, dependencies, and agent approach.

### Step 4: Execute via dependency graph

**IMPORTANT: Use a subagent for each sub-feature** to keep the context window clean. The main agent orchestrates; the subagent implements.

Do NOT rationalize skipping steps with: "This sub-feature is simple enough to implement inline", "I'll do the review at the end instead of per-group", or "The checkpoint is unnecessary since the previous group passed." If a step exists, execute it.

The dependency graph drives execution order. Loop until no ready issues remain:

```bash
planwise ready --children-of $ARGUMENTS
```

Each iteration: get ready issues -> implement them -> mark done -> get next ready batch. Issues with no dependencies on each other are naturally parallel — if `ready` returns multiple issues, dispatch them concurrently using `isolation: "worktree"`.

#### Subagent prompt template

Use this prompt structure for all implementation subagents:

   ```
   Implement sub-feature <sub-feature-slug> for feature $ARGUMENTS.

   Context:
   - Branch: <current branch name>
   - Previously completed sub-features: <list of completed sub-feature slugs and what they did>
   <if explore-first, include:>
   - Codebase exploration findings: <paste explore agent output>

   Instructions:
   1. Read the sub-feature: planwise view <sub-feature-slug>
   2. Implement following the full sub-feature body: Requirements, Edge Cases & Error Handling, Constraints, and Implementation Recipe.
      - Use the recipe's Files & Patterns section to know where to change and what shape to follow.
      - Always Read a file immediately before editing it. Use exact content from the Read output as old_string.
      - Follow the rules (from the Rules section above). No scope creep. Do not refactor surrounding code.
      - Scope boundary: You may ONLY modify files listed in the recipe's Files & Patterns section. If you believe an unlisted file needs changing, report BLOCKED — do not modify it yourself.
      - If the codebase doesn't match what the recipe describes (files missing, patterns changed), STOP and report BLOCKED with the specific discrepancy.
      - If during implementation you discover the recipe's approach is fundamentally flawed (not just a missing file — a wrong architectural assumption), STOP and report REPLAN with: what the recipe assumes, what's actually true, and a suggested fix. Do not implement a known-bad approach just because the recipe says to.
   3. Run the Validation command from the recipe.
   4. Write unit/integration tests that verify the Requirements and Edge Cases.
   5. Verify all Acceptance Criteria are addressed before committing.
   6. Commit:
      git add -A
      git commit -m "<type>: <description> (#<sub-feature-slug>)"
      Commit types: feat, fix, ref, test, docs, chore, style. Use imperative mood, focus on outcomes.
   7. Report back with a status, summary, and evidence:
      - DONE — what was implemented, files changed. Paste test output as evidence if applicable.
      - DONE_WITH_CONCERNS — implemented, but something feels wrong or fragile. Describe the concern. Paste test output as evidence if applicable.
      - BLOCKED — cannot proceed. Describe what's missing or ambiguous.
      - REPLAN — what the recipe assumes vs what's actually true, and a suggested fix.
      Use DONE_WITH_CONCERNS over guessing silently. The main agent will decide how to proceed.

   If this is a bug fix (has `bug` label):
   - Trace the bad value backward through the call stack to the origin — fix at the root cause, not where the symptom appears.
   - If 3 fix attempts fail, stop patching and re-examine the architecture. Report back with findings instead of trying a 4th fix.
   - After fixing, demonstrate the test fails without the fix and passes with it.
   ```

#### For each batch of ready issues

1. **Move to in-progress:**
   ```bash
   planwise status <sub-feature-slug> in-progress
   ```

2. **If `explore-first` agent:** launch an Explore subagent first:
   ```
   Explore the codebase to understand patterns relevant to sub-feature <N>.
   Focus on: [files listed in sub-feature's Implementation Recipe]
   Report: key patterns, type signatures, naming conventions the implementation should follow.
   ```
   Feed the explore findings into the implementation subagent's context.

3. **Launch implementation subagent(s):**
   - **Single ready issue:** launch one subagent using the prompt template above.
   - **Multiple ready issues:** launch one subagent per issue concurrently using `isolation: "worktree"`. Each works in an isolated worktree. After all complete, merge worktree branches back sequentially and delete the merged branch:
     ```bash
     git merge <worktree-branch-1> --no-edit
     git branch -d <worktree-branch-1>
     git merge <worktree-branch-2> --no-edit
     git branch -d <worktree-branch-2>
     ```
     If merge conflict: delete the conflicting worktree branch (`git branch -D <branch>`), then fall back to sequential re-implementation of the conflicting sub-feature on the main branch.

4. **Handle subagent status:**
   - **BLOCKED:** STOP and report the blocker to the user. Do not proceed to the next sub-feature.
   - **REPLAN:** Pause execution. Evaluate the finding. Either fix the sub-feature body and re-dispatch, or escalate to the user if the fix changes the feature's scope.
   - **DONE_WITH_CONCERNS:** Review the concern. If real, fix before proceeding. If a judgment call, note for Step 5 review.
   - **DONE:** Proceed to close/hand off.

5. **Close or hand off:**

   Check if this sub-feature has the `bug` label (available in the `ready` output — no extra query needed).

   - **No `bug` label (regular sub-feature):** Close and move to **done**:
     ```bash
     planwise status <sub-feature-slug> done
     ```

   - **Has `bug` label:** Do NOT close. The user must verify the fix manually. Report:
     ```
     Bug fix for <sub-feature-slug> is implemented and tests pass.
     Please verify the fix manually, then close <sub-feature-slug> when satisfied.
     ```
     STOP here and wait for the user.

6. **Next iteration:** run `planwise ready --children-of $ARGUMENTS` again. Completing issues unlocks their dependents. Repeat until no ready issues remain.

### Step 5: Review subagent work

After all sub-features are implemented, the main agent reviews the cumulative changes. This catches issues that subagents — working in isolation — cannot see: cross-sub-feature inconsistencies, duplicated code, mismatched types, or naming drift.

**Review scope** — proportional to feature complexity:
- **Small (1-3 sub-features, no parallel groups):** Verify all sub-features against their Acceptance Criteria (step 2). Skip the cross-boundary integrity check (step 3) — with few sub-features, boundaries are minimal.
- **Medium (4-6 sub-features or has parallel groups):** Full review as described below.
- **Large (7+ sub-features):** Full review plus cross-module integration check.

1. **Build the review map:** Run `git diff --stat` and `git log --oneline` for the feature's commits. Group changed files by sub-feature (match commits to sub-feature slugs). Identify **boundary files** — files modified by multiple sub-features or files that import from files changed by different sub-features.

2. **Spec compliance check** — For each sub-feature, verify the implementation actually satisfies its Requirements and Acceptance Criteria. Distrust the subagent's self-report — read the code directly. Flag:
   - Requirements not implemented or only partially implemented
   - Scope creep (code added that no sub-feature requested)
   - Missing edge case handling listed in the sub-feature

3. **Cross-boundary integrity check** — This is what isolated subagents cannot verify. For each boundary file identified in step 1:

   a. **Type flow:** Trace the data type from origin to consumer across sub-feature boundaries. Read the actual code — verify that types flow correctly through all layers. A type in one sub-feature must not become a different type in another.

   b. **Import resolution:** For every new export added by a sub-feature, grep for its consumers. Verify the import path, name, and type signature match. Check for circular imports introduced by cross-sub-feature wiring.

   c. **Contract alignment:** If sub-feature A defines an API endpoint and sub-feature B consumes it, read both sides and verify: route path, HTTP method, request body shape, response body shape, error codes. Mismatches here are the #1 cross-subagent failure mode.

   d. **Shared state consistency:** If multiple sub-features touch the same store, schema, or shared data, verify they agree on shape and behavior.

4. **Code quality check** — After boundary integrity passes:
   - Duplicated logic: did two subagents write the same helper or utility independently?
   - Naming drift: same concept called different names across sub-features
   - Dead code: imports or functions added by an earlier sub-feature that a later sub-feature made redundant
   - Adherence to rules

   **Calibration — do NOT flag:**
   - Style differences between subagents if both follow the rules
   - Code that looks like scope creep but is explicitly in the recipe
   - Minor naming variations if the types are consistent across boundaries
   - Test structure differences if coverage is equivalent
   Only flag issues that would cause real problems in production or review.

5. **If issues are found:** Fix them and commit with a message describing what was actually fixed:
   ```bash
   git add -A
   git commit -m "ref: <describe the specific fix> (#$ARGUMENTS)"
   ```

6. **If everything looks clean:** Proceed to the next step.

### Step 6: Move UAT to ready

Find the UAT sub-feature:

```bash
planwise list --children-of $ARGUMENTS --type uat | jq -r '.[0].id'
```

Only move UAT to **ready** if all coding sub-features are **done**. If any bug-labeled sub-features are pending user verification, skip this step — UAT waits until the user closes them.

```bash
planwise status <uat-number> ready
```

### Step 8: Move feature to in-review

```bash
planwise status $ARGUMENTS in-review
```

### Step 9: Report

Use Done for regular tasks, Pending for bug fixes left open.

```
All coding sub-features for Feature $ARGUMENTS are complete.

Summary:
- 51 — [title] (X tests written, all passing) Done
- 52 — [title] (X tests written, all passing) Done
- 53 — [title] (X tests written, all passing) Pending — Bug fix awaiting your verification

Branch: feat/<topic>
Commits: X commits

Retrospective:
- Assumption that was wrong or took longer than expected: [X]
- What to do differently next time: [Y]

Next steps:
1. Push the branch: git push --force-with-lease -u
2. Verify any open bug fixes and close them when satisfied
3. Work through the test checklist in the [UAT] sub-feature
4. When all tests pass, close the UAT and feature, then tell me to create the PR

Next:  /next
Tip: /clear or /compact first if context is heavy.
```
