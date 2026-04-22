# Phase 2 — Dispatchable protocols

This file is read by subagents spawned from `plan.md`. Main thread does NOT read it.

## Impact analysis

Trace the blast radius of the planned changes.

If the orchestrator passes KB Connections from Phase 1, start with them — they map known upstream/downstream dependencies and shared types. Use as starting point, then verify and extend with code-level analysis.

For each file in the Technical Context the orchestrator passes:
- Grep for imports/usages of the types, schemas, and interfaces that will change.
- Identify downstream consumers the feature doesn't mention — these are hidden dependencies.
- Cross-check against KB Connections — are there known ripple effects the code search missed?

### Return shape

Return a table of downstream consumers:

| Symbol | Downstream file | Consumer kind (import / call / subclass) | Already in feature scope? |

Mark every row whose file is not in the Technical Context as a **hidden dependency**. The orchestrator decides whether to fold each hidden dependency into an existing sub-feature or raise it to the user.

## Pre-mortem + Risk stress-test

Do NOT rationalize skipping: "This is straightforward enough to skip", "The sub-features are clear enough", or "I'll verify during implementation." Execute every step.

### Pre-mortem

Imagine the feature was implemented and the feature does not work. What plausible failure scenarios exist? For each, check if the current plan prevents it.

### Risk stress-test

Stress-test the plan against these risks:
- Edge cases not covered?
- Security or data implications?
- Migration or backward compatibility needs?
- Accessibility requirements?
- Dependencies on other features or teams?
- Performance implications at scale?
- Observability: what should be logged, monitored, or alerted on?

For each risk: is it mitigated by the plan, or does the plan need to change?

### Self-challenge

Challenge the output: are any risks false positives? Is the plan over-scoped? Is this the simplest approach that solves the problem?

If genuine technical unknowns surface, state them — the orchestrator will investigate the codebase or raise to the user before committing to the plan.

### Return shape

Return:
- Failure scenarios: list of `{scenario, likelihood, mitigated-by-current-plan?, if not, what changes the plan needs}`
- Self-challenge: `{over-scoped? simpler-approach? false-positive risks?}`
- Technical unknowns (if any): list of `{unknown, why it matters, what to investigate}`
