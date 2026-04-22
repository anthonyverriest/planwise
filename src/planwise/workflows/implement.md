---
description: "Implement all coding sub-features for a feature (automated, concurrent-safe)"
---

# Implement Feature $ARGUMENTS

Implement every coding sub-feature of $ARGUMENTS in dependency order.

**Assumed context:** this workflow runs inside a fresh jj workspace created by `pw claude`. Inter-feature concurrency (two features in parallel) is handled by the CLI — each `pw claude` session is its own sandbox off `dev@origin`, so parallel runs never share `@`. Intra-feature concurrency (sub-features in parallel) happens inside this workspace via subagent git worktrees.

## Step 1 — Preflight

```bash
planwise view $ARGUMENTS
planwise view $ARGUMENTS --field status
```

If status is `in-progress`, STOP — another run owns this feature. Other features being `in-progress` is fine (that's the inter-feature parallelism working). Otherwise:

```bash
planwise status $ARGUMENTS in-progress
```

Derive a kebab-case topic from the feature title. Prefix: `feat/` for features, `fix/` for fixes.

## Step 2 — Anchor the feature bookmark

If `feat/<topic>` does not already exist, create it on `@`:

```bash
jj bookmark list | grep -q "^feat/<topic>" || jj bookmark create feat/<topic> -r @
```

Refresh trunk and rebase the entire feature stack onto it. Rebase never aborts on conflict in jj — conflicts are recorded inline as data. Use `-b @` so every feature change gets rebased, not just `@`.

```bash
jj git fetch
jj rebase -b @ -d dev@origin
```

After rebase, check for conflicts:

```bash
jj resolve --list
```

For each conflicted path: Read the file, `jj show` the trunk change that introduced the conflicting side to recover intent, then classify:
- **Mechanical** (imports, formatting, non-overlapping additions, one-side deletes) → resolve inline.
- **Semantic** (both sides changed the same logic with different intent) → STOP, show the user the conflicted paths and both sides, ask which intent to keep. Do not guess.

`jj status` must report no remaining conflicts before continuing.

jj auto-snapshots the working copy on every command. Do not call `git` directly in this workspace — colocated git state is kept in sync by jj.

## Rules

$RULES

## Step 3 — Execute dependency graph

Loop until `planwise ready --children-of $ARGUMENTS` returns nothing. Each iteration:

### 3a. Fetch the ready batch

```bash
planwise ready --children-of $ARGUMENTS
```

Returns coding sub-features with no unmet dependencies (UAT and bugs excluded from scheduling; bug-labeled sub-features carry a `bug` label).

### 3b. Mark each in-progress

```bash
planwise status <slug> in-progress
```

### 3c. Dispatch — one subagent per sub-feature, always in a worktree

Do NOT rationalize skipping steps with: "This sub-feature is simple enough to implement inline", "I'll do the review at the end instead of per-group", or "The checkpoint is unnecessary since the previous group passed." If a step exists, execute it.

Use the Agent tool with `isolation: "worktree"` for every sub-feature, even when the batch has only one. Uniform dispatch removes the serial/parallel fork. The Agent tool spawns the worktree from the current workspace's HEAD, so sub-features branch off the latest feature tip automatically.

If a sub-feature's agent approach is `explore-first`, launch an Explore subagent first and feed findings into the implementation prompt.

For each ready sub-feature, dispatch:

> Read `src/planwise/workflows/_implement/execute.md` § **Sub-feature implementation**.
> Inputs:
> - Feature slug: `$ARGUMENTS`
> - Sub-feature slug: `<slug>`
> - Completed so far: `<slugs + one-line summaries>`
> - Explore findings (if explore-first): `<paste or "None">`
> - Rules: `<paste $RULES>`
>
> Return the report per § **Return contract**. If the sub-feature carries the `bug` label, follow § **Bug label branch**.

### 3d. Reconcile returned work into the feature change

After all dispatched subagents return, import their git refs:

```bash
jj git import
```

Let `N` = number of DONE / DONE_WITH_CONCERNS sub-features. BLOCKED and REPLAN contribute no commits.

- **N == 1:** the sub-branch already descends from the feature tip; advance `@` to it.
  ```bash
  jj edit sub/<slug>@git
  ```

- **N > 1:** n-way merge the parallel branches onto the current feature tip.
  ```bash
  jj new @ sub/<slug-a>@git sub/<slug-b>@git ... -m "merge: <slugs> (#$ARGUMENTS)"
  ```

Check for conflicts:

```bash
jj resolve --list
```

For each conflicted path: Read the file, `jj show sub/<slug>@git` on each side to recover intent, then classify:
- **Mechanical** → resolve inline.
- **Semantic** (both sub-features changed the same logic with different intent) → STOP, show the user the paths and both sides, ask which intent to keep. Do not guess.

When resolving across parallel sub-features, apply Step 4's boundary checks (type flow, contract alignment, shared state). Edits land on the merge change via jj's auto-snapshot — no squash needed. `jj status` must report no remaining conflicts before continuing.

Clean up every consumed `sub/<slug>` git ref — both the N==1 and N>1 paths — so batches don't accumulate stale branches (the Agent tool reclaims the worktree itself, but leaves the ref):

```bash
git branch -D sub/<slug-a> [sub/<slug-b> ...]
jj git import
```

### 3e. Handle statuses and close

- **DONE / DONE_WITH_CONCERNS** (no `bug` label):
  ```bash
  planwise status <slug> done
  ```
- **DONE** with `bug` label: leave open — user verifies manually. Report explicitly in the final summary.
- **BLOCKED:** STOP the run; report the blocker.
- **REPLAN:** STOP; report the finding. Either patch the sub-feature body and re-dispatch, or escalate.

Re-run `planwise ready --children-of $ARGUMENTS`. Repeat until empty.

## Step 4 — Cross-boundary review

Main agent reviews cumulative work for issues isolated subagents cannot see.

1. **Build the map:**
   ```bash
   jj diff --from dev@origin --stat
   jj log -r 'dev@origin..@' -T builtin_log_oneline
   ```
   Group changed files by sub-feature (via commit descriptions). A **boundary file** is any file touched by >1 sub-feature or importing across sub-feature boundaries.

2. **Skip condition:** if zero boundary files AND zero `DONE_WITH_CONCERNS` reports, skip to step 4.

3. **Dispatch — Cross-boundary reviewer (general-purpose, fresh context)**

   > Read `src/planwise/workflows/_implement/review.md` § **Spec compliance**, § **Cross-boundary integrity**, § **Code quality**.
   > Inputs:
   > - Feature slug: `$ARGUMENTS`
   > - Changed files grouped by sub-feature: `<paste>`
   > - Boundary files (touched by >1 sub-feature): `<paste or "None">`
   > - Sub-feature bodies: `<paste planwise view outputs from Step 3>`
   > - Implementer concerns: `<concatenated DONE_WITH_CONCERNS text from Step 3c, or "None">`
   > - Rules: `<paste $RULES>`
   >
   > Return findings per § **Return contract**.

4. **If findings returned,** fix and commit:
   ```bash
   jj commit -m "ref: <specific fix> (#$ARGUMENTS)"
   ```

## Step 4.5 — Generate review tour

The PR body is a tour — a reading order over the diff that tells the reviewer where to start, what is subtle, which decisions are worth knowing, and what to skip. Generated once, used as `gh pr create --body` in Step 5.

### Collect inputs (main thread)

```bash
jj diff --from dev@origin --stat
jj diff --from dev@origin
jj log -r 'dev@origin..@' -T builtin_log_oneline
```

Bundle alongside:
- Feature slug: `$ARGUMENTS`
- Sub-feature bodies: the per-sub-feature `planwise view` output already in context from Step 3
- Implementer concerns: concatenated `DONE_WITH_CONCERNS` concern text from Step 3c reports, or `"None"`
- Cross-boundary findings: flagged items from Step 4, or `"None"`

### Dispatch — Tour writer (general-purpose, fresh context)

> Read `src/planwise/workflows/_implement/tour.md` § **Tour writer**. Inputs:
> - Feature slug: `$ARGUMENTS`
> - Diff stat: `<paste jj diff --stat output>`
> - Patch: `<paste jj diff output>`
> - Commit log: `<paste jj log output>`
> - Sub-feature bodies: `<paste>`
> - Implementer concerns: `<paste or "None">`
> - Cross-boundary findings: `<paste or "None">`
>
> Return the tour Markdown per the protocol's output contract. No preamble, no trailing commentary.

### Sanity check (main thread)

Reject and re-dispatch once if any of these fail:
- Every `path:Lxx` or `path:Lxx-Lyy` cited appears in `jj diff --from dev@origin --name-only`
- Stop count ≤ 10
- Each stop is a single sentence
- At least one Skip stop exists when 3+ files have `|` change bars mostly at the edges of `--stat` (renames/mechanical)

If it fails twice, fall back to this body and log `tour generation failed` in the Step 5 report:

```markdown
Tour unavailable — see plan: `planwise view $ARGUMENTS`

Closes #$ARGUMENTS
```

Hold the final tour Markdown in a variable `TOUR_BODY` for Step 5.

## Step 5 — Finalize

Move UAT to ready only if every coding sub-feature is `done` (bug-labeled sub-features pending user verification block this):

```bash
planwise list --children-of $ARGUMENTS --type uat | jq -r '.[0].id'
planwise status <uat-slug> ready
```

Move the feature:

```bash
planwise status $ARGUMENTS in-review
```

Advance the bookmark to the feature tip. The revset picks the highest non-empty change in `dev@origin..@`, correct whether `@` is the tip or an empty change above it:

```bash
jj bookmark set feat/<topic> -r 'heads(dev@origin..@ ~ empty())'
```

If jj rejects as non-fast-forward, investigate — do not force with `--allow-backwards`.

Report:

```
Feature $ARGUMENTS complete.

Workspace: <path to feature workspace>

Sub-features:
- <slug> — <title> Done
- <slug> — <title> Pending — bug fix awaiting verification
...

Bookmark: feat/<topic>
Commits: <N>

Retrospective:
- Wrong assumption or surprise: <X>
- Next time: <Y>

Next steps:
1. Push:      jj git push --bookmark feat/<topic>
2. PR (copy-run — the --body is the review tour from Step 4.5):

     gh pr create --base dev --head feat/<topic> \
       --title "<feature title>" \
       --body "$(cat <<'EOF'
     <paste TOUR_BODY verbatim>
     EOF
     )"

3. Verify open bug fixes; close when satisfied.
4. Work the UAT checklist; close UAT and feature when green.
5. After merge, free the workspace (name was echoed when `pw claude` created it):
     cd <main repo root>
     jj workspace forget <workspace-name>
     rm -rf <workspace path>


Next: /next
Tip: /clear or /compact first if context is heavy.
```
