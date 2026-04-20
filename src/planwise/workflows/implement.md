---
description: "Implement all coding sub-features for a feature (automated mode)"
---

# Implement Full Feature (Automated)

Implement all coding sub-features for a feature following its dependency graph.

## Target: Feature $ARGUMENTS

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

Understand the full scope, the WHAT and WHY. Note the feature title — you will derive the bookmark name from it.

Move the feature to **in-progress**:

```bash
planwise status $ARGUMENTS in-progress
```

### Step 2: Create or switch to the feature change

Work **anonymously via change-id** during iteration — a named bookmark is only needed at push time (Step 7). This avoids bookmark churn if the feature is reworked or abandoned.

Check if an in-progress feature change for this slug already exists (from a previous `/implement` run). Features are identified by the slug suffix `(#$ARGUMENTS)` in their description, and we want the latest one that has not yet been merged into `dev@origin` (covers both local-only and pushed-but-unmerged cases):

```bash
jj log -r 'description(glob:"*(#$ARGUMENTS)*") & ~::dev@origin' --limit 1 -T 'change_id.short()'
```

- **Change exists:** Switch to it.
  ```bash
  jj edit <change-id>
  ```

- **No change yet:** Create a new change off the latest `dev`.
  ```bash
  jj git fetch
  jj new dev@origin -m "feat: <short description> (#$ARGUMENTS)"
  ```

Record the change-id returned by jj — the orchestration below refers to it as `<feature-change-id>`. Also note a kebab-case topic (derived from the feature title; used in Step 7 as the bookmark name). Prefix matches intent: `feat/` for features, `fix/` for fixes (e.g., `feat/club-preferences`, `fix/member-search`).

**Stale-trunk check:** if the feature change already existed and `jj git fetch` pulled new commits on `dev@origin`, rebase before resuming work: `jj rebase -d dev@origin` (on the feature change). Rebase never blocks — jj records conflicts as data. Then run the **conflict resolution protocol** (see below) before proceeding.

### Conflict resolution protocol

After any rebase or merge, check for conflicts:
```bash
jj resolve --list
```

For each conflicted path:
1. Read the file. jj has materialized conflict markers (`<<<<<<<`, `|||||||`, `=======`, `>>>>>>>`).
2. `jj show` the trunk change that introduced the conflicting side — recover its intent.
3. Classify:
   - **Mechanical** (imports, formatting, non-overlapping additions, one side deletes what the other doesn't touch) → resolve inline. Edit the file to produce the coherent merged result.
   - **Semantic** (both sides changed the same logic with different intent) → STOP. Show the user the conflicted paths, the diff from each side, and ask which intent to keep. Do not guess.
4. After resolution, `jj status` must report no remaining conflicts before continuing.

jj auto-snapshots the working copy on every command — there is no staging area. Do not invoke `git` directly; co-located git state is kept in sync by jj.

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
   - Feature change-id: <feature-change-id> (the shared parent; your work will land as a descendant of this change)
   - Previously completed sub-features: <list of completed sub-feature slugs, their change-ids, and what they did>
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
   6. Commit — mechanism depends on how you were dispatched:

      **Serial (no isolation):** you are in the main jj workspace. Use jj:
        jj commit -m "<type>: <description> (#<sub-feature-slug>)"
        # Capture and report the change-id of what you just committed:
        jj log -r @- --no-graph -T 'change_id.short()'
      Report the resulting `<final-change-id>` — the main agent uses it for Step 5 review tracking.

      **Parallel (isolation: "worktree"):** you are in a git worktree that is NOT a jj workspace. Use git:
        git checkout -b sub/<sub-feature-slug>
        git add <specific-files>        # or -A if scope is the whole worktree
        git commit -m "<type>: <description> (#<sub-feature-slug>)"
        # Capture and report the commit hash:
        git rev-parse HEAD
      Report the resulting `<commit-hash>` — the main agent uses it for the n-way jj merge after importing refs.

      Commit types: feat, fix, ref, docs, chore, style. Use imperative mood, focus on outcomes.
      Reserved workflow prefixes — do NOT use from /implement: `test:` (emitted by /test, greppable signal for /memo Phase 2) and `optimize:` (emitted by /optimize, greppable signal for /memo Phase 2). These live in the commit subject so /memo can discover them without parsing bodies.
   7. Report back with a status, summary, and evidence. Include the **handle** from step 6 (a jj change-id if you ran serially, a git commit hash if you ran in an isolated worktree):
      - DONE — what was implemented, files changed, **handle**. Paste test output as evidence if applicable.
      - DONE_WITH_CONCERNS — implemented, but something feels wrong or fragile. Describe the concern. Include **handle**. Paste test output as evidence if applicable.
      - BLOCKED — cannot proceed. Describe what's missing or ambiguous. (No handle needed.)
      - REPLAN — what the recipe assumes vs what's actually true, and a suggested fix. (No handle needed.)
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
   - **Multiple ready issues:** launch one subagent per issue concurrently using `isolation: "worktree"` (the Agent tool's isolation parameter creates a **git worktree** sharing `.git` with the main workspace). In a colocated jj repo, git commits made inside that worktree are backend-visible to jj in the main workspace after a `jj git import`, which is exactly how the main agent reconciles parallel work below.

     **Why subagents commit via git, not jj:** an Agent-tool worktree has its own git index but no `.jj/working_copy/` metadata, so it is not a jj workspace. The subagent cannot safely run `jj commit` there. Subagents use `git` inside their worktree; the main agent (on a real jj workspace) does all jj operations.

     Each subagent, inside its isolated worktree:
     ```bash
     git checkout -b sub/<sub-feature-slug>
     # edit, test, etc.
     git add <specific-files>        # or -A if scope is the whole worktree
     git commit -m "<type>: <description> (#<sub-feature-slug>)"
     git rev-parse HEAD              # capture the sub-feature commit hash to report back
     ```
     Require each subagent to report its final **git commit hash** in the DONE/DONE_WITH_CONCERNS response. The main agent treats these hashes as handles for the merge below — no bookmarks needed.

     After all subagents return, the main agent **imports the new git refs** so jj sees them as changes:
     ```bash
     jj git import
     ```
     Each reported git commit hash now resolves to a jj change. The main agent merges them into the feature change in **one n-way merge** (conflicts are recorded inline, not fatal):
     ```bash
     jj new <feature-change-id> <sub-commit-hash-1> <sub-commit-hash-2> ... <sub-commit-hash-N> -m "merge: sub-features for $ARGUMENTS (#$ARGUMENTS)"
     ```
     jj accepts commit hashes and change-ids interchangeably as revision specifiers.

     **Inspect for conflicts:**
     ```bash
     jj status
     jj resolve --list
     ```

     If `jj resolve --list` reports conflicted paths, resolve them **inline here**, in this phase — do not defer, do not abandon work:

     a. For each conflicted path, Read the file. jj has materialized conflict markers (`<<<<<<<`, `|||||||`, `=======`, `>>>>>>>`) in place.
     b. Apply the same cross-sub-feature review logic that Step 5 uses (type flow, import resolution, contract alignment, shared-state consistency) to decide the correct unified content. Edit the file to remove the markers and produce a coherent result.
     c. After all files are resolved: `jj status` should report no remaining conflicts. The auto-snapshot has already absorbed your edits into the merge change (`@`); no explicit squash needed.

     d. Clean up the temporary sub-feature branches once merged. The Agent tool auto-reclaims the worktree directory when the subagent returns — do not remove it manually:
        ```bash
        git branch -D sub/<sub-feature-slug>    # delete the temporary sub-feature branches
        jj git import                            # re-import so jj forgets the deleted git refs
        ```

     **No work is ever discarded.** jj records conflicts as data in the change graph; resolution is an edit, not a re-implementation. Once merged, jj's change-ids for the sub-feature work are stable across subsequent amends — the ledger reference survives.

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

1. **Build the review map:** Run `jj diff --from dev@origin --stat` and `jj log -r 'dev@origin..@' -T builtin_log_oneline` for the feature's commits. Group changed files by sub-feature (match commit descriptions to sub-feature slugs). Identify **boundary files** — files modified by multiple sub-features or files that import from files changed by different sub-features.

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
   jj commit -m "ref: <describe the specific fix> (#$ARGUMENTS)"
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

### Step 7: Move feature to in-review and anchor the bookmark

```bash
planwise status $ARGUMENTS in-review
```

Now — and only now — anchor the named bookmark on the tip of the feature work. Throughout iteration you worked anonymously via change-ids; push requires a named bookmark.

Use a revset to find the feature head robustly — `@-` is **not** reliable here because after a parallel n-way merge with no review-fix commit, `@` is itself the merge/feature head (not an empty working-copy change on top of one):

```bash
FEATURE_HEAD=$(jj log -r 'heads(dev@origin..@ ~ empty())' --no-graph -T 'change_id.short()' --limit 1)
jj bookmark create feat/<topic> -r "$FEATURE_HEAD"
```

The revset `dev@origin..@ ~ empty()` selects all non-empty changes between `dev@origin` and `@`; `heads(...)` picks the tip. This is correct whether the feature ends at the merge change itself or at a review-fix commit above it.

If a bookmark with the same name already exists from a prior run, move it forward:

```bash
jj bookmark set feat/<topic> -r "$FEATURE_HEAD"
```

jj will reject a non-fast-forward move without `--allow-backwards`. If the move is rejected, investigate — it usually means the bookmark was rewound elsewhere and the new head is behind it. Do not force with `--allow-backwards`; fix the underlying cause.

### Step 8: Report

Use Done for regular tasks, Pending for bug fixes left open.

```
All coding sub-features for Feature $ARGUMENTS are complete.

Summary:
- 51 — [title] (X tests written, all passing) Done
- 52 — [title] (X tests written, all passing) Done
- 53 — [title] (X tests written, all passing) Pending — Bug fix awaiting your verification

Bookmark: feat/<topic>
Commits: X commits

Retrospective:
- Assumption that was wrong or took longer than expected: [X]
- What to do differently next time: [Y]

Next steps:
1. Push the bookmark: jj git push --bookmark feat/<topic>
2. Open the PR: gh pr create --base dev --head feat/<topic> --title "<feature title>" --body "Closes #$ARGUMENTS"
3. Verify any open bug fixes and close them when satisfied
4. Work through the test checklist in the [UAT] sub-feature
5. When all tests pass, close the UAT and feature

Next:  /next
Tip: /clear or /compact first if context is heavy.
```
