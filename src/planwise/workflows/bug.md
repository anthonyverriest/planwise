---
description: Report a bug found during UAT and create a bug sub-feature linked to the feature
---

# Report a Bug Found During User Testing

Create a bug sub-feature linked to an feature, found during user acceptance testing.

## Input

$ARGUMENTS

The first number is the feature number. Everything after it is the bug description.
Example: `50 Theme toggle does not persist after page refresh`

## Process

### Step 1: Read the feature and its sub-features

```bash
planwise view <feature-slug>
planwise list --children-of <feature-slug>
```

Understand the full feature context and what coding sub-features were implemented.

### Step 2: Understand the bug

Read the user's description. Investigate the codebase to understand the likely cause.

Only use `AskUserQuestion` tool to ask clarifying questions if the bug is genuinely ambiguous — a well-written description is usually sufficient.

### Step 3: Create the bug sub-feature

```bash
echo "<bug body — see template below>" | planwise create bug "Fix: <concise bug description>" --parent <feature-slug>
```

**Bug sub-feature body — ALL sections required:**

```
## Context
Part of Feature <feature-slug> — [feature title].
Found during user acceptance testing (<uat-number>).

## Bug Description
**What happens:** [current broken behavior]
**What should happen:** [expected correct behavior]
**Steps to reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Requirements
1. [Precise fix requirement — what needs to change]
2. [Continue as needed — each must be testable]

## Edge Cases & Error Handling
- [Related scenarios to verify aren't also broken]
- [Boundary conditions around the bug]
- [Error states that may be affected]

## Constraints
- MUST NOT break: [existing behavior to preserve]
- MUST NOT change: [API contract, schema, or UI behavior]
(Use "None" if this fix has no regression-sensitive boundaries.)

## Implementation Notes
[Likely cause based on reviewing the feature and codebase.
Suggested approach and patterns to follow.
Reference CLAUDE.md where relevant.
MUST include exact file paths to investigate or modify (use `@package/path:line` where relevant).
MUST NOT contain placeholder language — every instruction must be actionable as written.]

## Acceptance Criteria
- [ ] Bug no longer reproduces following steps above
- [ ] All requirements verified
- [ ] Unit and integration tests written and passing

## Dependencies
[Blocked by <XX> or "None"]
```

### Step 4: Report

```
Bug sub-feature created: <new-number> — Fix: <description>
Linked to Feature <feature-slug>

To fix it, run: /implement <feature-slug>
(The implement command will pick up this open sub-feature.)

After the fix is implemented, verify it manually via the UAT checklist in <uat-number>.
```
