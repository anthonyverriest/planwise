---
description: "Run a sync pipeline step-by-step with human supervision"
---

# Sync Pipeline

Run a sync pipeline with automated execution and human supervision. The agent executes each step, diagnoses failures, attempts fixes, and pauses at human gates for approval.

## Target pipeline: <the user's task>

Default pipeline path: `planwise/sync.yml`. If `<the user's task>` is a path to a YAML file, use that instead.

## Process

### Step 1: Load and display the pipeline

```bash
planwise sync show --pipeline <path>
```

**If the command fails** (file not found, YAML parse error, invalid schema): report the error and stop.

Review the pipeline steps, their plugins, and gate types.

**If state already exists** (some steps show non-pending status): ask the user whether to resume from where they left off, or reset and start fresh:

```bash
planwise sync reset --all
```

**If no state exists**: confirm with the user before starting.

Use `AskQuestion` if available (fallback: ask in chat): **"Pipeline '<name>' has N steps. Ready to start?"**

### Step 2: Walk the pipeline

Execute each step sequentially. For each step:

#### 2a. Pre-execution gate (human steps only)

If the step has `gate: human`, show the step details before executing:

- Step name and index
- Plugin and action (or inline command)
- What the command will do

Use `AskQuestion` if available (fallback: ask in chat): **"Step N: '<name>' — <description>. Approve, skip, or abort?"**

- **approve**: proceed to execution
- **skip**: mark step as skipped, continue to next
- **abort**: save state, stop the pipeline. The user can resume later with `/sync`

#### 2b. Precondition check

Before executing, check if any prior step that this step depends on was **skipped** or **failed**. If so:

Use `AskQuestion` if available (fallback: ask in chat): **"Step N: '<name>' depends on '<prior step>' which was <skipped/failed>. Proceed anyway, skip, or abort?"**

#### 2c. Execute the step

```bash
planwise sync exec <step_name> --pipeline <path>
```

Read the JSON result carefully.

#### 2d. Handle the result

**Success or fixed** — report briefly and continue to the next step.

**Failed with matched failure and fix was attempted but didn't work** (`status: "fix_attempted"`):

Report what happened:
1. The original failure and what pattern matched
2. What fix was attempted
3. That the fix didn't resolve the issue

Then reason about the failure:
- Read the `plugin_context` field from the result — it contains tool-specific knowledge for diagnosing the issue
- Examine relevant files in the codebase based on the error output
- Propose a different fix

Use `AskQuestion` if available (fallback: ask in chat): **"Step '<name>' failed. <diagnosis>. I'd like to try: <proposed fix>. Approve?"**

If approved, execute the fix, then re-run the step:
```bash
planwise sync exec <step_name> --pipeline <path> --force
```

**Failed with matched failure but no fix available** (`status: "failed"`, `matched_failure` is set, no `fix_command`):

The plugin knows what went wrong but has no automated fix. This is where you reason:
1. Read the matched failure message
2. Read the `plugin_context` field from the result — it contains tool-specific knowledge
3. Examine the codebase — look at the files and state relevant to the error
4. Cross-reference with other pipeline steps — does this failure relate to another tool's state?
5. Propose a fix based on your analysis

Use `AskQuestion` if available (fallback: ask in chat): **"Step '<name>' failed: <matched failure message>. After investigating, I believe: <diagnosis>. Proposed fix: <fix>. Approve?"**

If approved, execute the fix, then re-run:
```bash
planwise sync exec <step_name> --pipeline <path> --force
```

**Failed with no matched failure** (`status: "failed"`, no `matched_failure`):

Unknown failure — this is the key scenario where cross-tool reasoning provides value.

1. Read the full stdout and stderr from the result
2. Read the `plugin_context` field — it contains tool-specific knowledge for diagnosing unknown failures
3. Search the codebase for files related to the error
4. Check if the failure relates to a previous step's output or another tool's state
5. Trace the error across tool boundaries if needed (e.g., a migration failing because infrastructure hasn't been provisioned yet)

Use `AskQuestion` if available (fallback: ask in chat): **"Step '<name>' failed with an unexpected error. <full analysis>. Proposed fix: <fix>. Approve?"**

If approved, execute the fix, then re-run:
```bash
planwise sync exec <step_name> --pipeline <path> --force
```

**If 3 fix attempts fail for the same step**, stop trying and escalate:

Use `AskQuestion` if available (fallback: ask in chat): **"Step '<name>' has failed 3 times. <summary of attempts>. Would you like to: skip this step, abort the pipeline, or tell me what to try?"**

### Step 3: Completion report

After all steps complete (or the pipeline is aborted):

```bash
planwise sync state
```

Present a summary:

```
Pipeline '<name>' complete.

Results:
  1. [SUCCESS] <step-name>
  2. [FIXED]   <step-name> — was: <original failure>, fixed by: <what was done>
  3. [SKIPPED] <step-name>
  4. [FAILED]  <step-name> — <failure description>

N/M steps succeeded.
```

If all steps succeeded: **"Pipeline complete. All steps passed."**

If some steps failed: **"Pipeline finished with failures. Review the failed steps above."**

If aborted: **"Pipeline paused at step N. Run /sync to resume."**
