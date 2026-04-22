# Test — Analysis protocols

This file is read by subagents spawned from `test.md`. Main thread does NOT read it.

## Functional coverage analysis

You are defining what "working correctly" means. The adversarial stage will then try to violate it.

IMPORTANT: Do NOT modify any non-test files. You are analyzing, not fixing.

Analyze the target's public API and identify test cases that verify the behavioral contract.

Categories to cover:
- **Happy paths:** primary use cases with valid inputs → expected outputs
- **Error contracts:** documented/expected error behavior for known invalid inputs (not adversarial — these are errors the code explicitly handles)
- **State transitions:** valid state changes produce correct results, invariants hold
- **Integration contracts:** components interact correctly at boundaries (caller → callee, request → response shape)
- **Boundary values:** valid edges — min/max of accepted ranges, empty-but-valid inputs

Do not invent failure scenarios — that's the adversarial stage. Focus on what the code is SUPPOSED to do.
Report at most 10 test cases. Prioritize untested public API surface.

### Return contract (functional)

For each test case, report:

```
### Test: [title]
**Behavior:** [what the code promises — expected input → expected output/effect]
**Type:** happy-path | error-contract | state-transition | integration-contract
**Target:** @file:line
**Test sketch:** [2-3 line pseudocode]
**Needs:** [existing helper, new fixture, etc.]
```

## Adversarial dimension analysis

You are trying to BREAK this code. The functional contract (provided as input) defines what "working" looks like — find inputs, states, and conditions that violate it. Use the recon catalog as your starting point — do not re-read target files unless you need to examine a specific code path in detail.

IMPORTANT: Do NOT modify any non-test files. You are analyzing, not fixing.

Focus exclusively on the dimension named in your input. Dimension definitions are in § **Dimensions** below.

Report at most 5 attack vectors. Prioritize by likelihood of finding a real bug.

### Return contract (adversarial)

For each attack vector, report:

```
### Attack: [title]
**Hypothesis:** "I believe [specific input/condition] will cause [specific failure] because [reasoning]"
**Vector:** [dimension]
**Severity:** CRITICAL / HIGH / MEDIUM
**Target:** @file:line
**Test sketch:** [2-3 line pseudocode showing the test approach]
**Needs:** [what test infrastructure is required — existing helper, new fixture, docker, etc.]
```

## Dimensions

### Dimension 1: Input abuse
Malformed, oversized, empty, null-equivalent, unicode edge cases, type confusion, injection payloads (SQL, OS command, header, path traversal, SSTI/template injection), XSS via stored/reflected input, SSRF through user-controlled URLs, CSRF token bypass, denormalized strings (whitespace-only, zero-width chars, RTL overrides), boundary values (0, -1, max integer, empty string vs null/None).

### Dimension 2: Auth & access control
Token manipulation (expired, future-dated, wrong algorithm, missing claims, extra claims, malformed base64), BOLA/IDOR (accessing resources by manipulating object IDs), BFLA (calling admin/privileged endpoints as regular user), missing authentication on critical functions, privilege escalation (horizontal and vertical), session state attacks (revoked but cached, race between revocation and use), MFA bypass attempts, cookie injection/smuggling.

### Dimension 3: Concurrency & race conditions
TOCTOU between check and use, concurrent mutations to shared state, lock contention under parallel requests, task cancellation mid-operation, cancel-safety violations in async runtimes, channel/queue backpressure, concurrent idempotency key usage, double-spend/duplicate processing from concurrent submissions.

### Dimension 4: Resource exhaustion & limits
Oversized request bodies, header flooding, connection exhaustion, memory pressure from unbounded collections, slow-loris style attacks, rate limit bypass attempts, idempotency store growth without cleanup, ReDoS (catastrophic regex backtracking), decompression bombs (zip/gzip), XXE expansion (billion laughs).

### Dimension 5: State corruption & invariants
Invalid state transitions, partial updates that violate invariants, orphaned records, stale cache entries, insecure deserialization (pickle.loads, yaml.load, jsonpickle — code execution via crafted payloads), deserialization into inconsistent state, strict-mode deserialization bypass, mass assignment (unexpected fields overwriting protected attributes), timestamp manipulation, timezone handling errors.

### Dimension 6: Error handling & dependency resilience
Error message information leakage (stack traces, internal paths, SQL errors, PII/tokens/secrets in logs or responses), error type confusion (wrong status code for error class), unhandled runtime failures (unguarded exceptions, unchecked error returns), silent error swallowing (discarded results, ignored return values). Upstream failure modes: external service timeouts, 5xx responses, partial/malformed responses, retry storms, circuit breaker behavior, outbox consistency under failure, cascading failures from dependency errors, unsafe consumption of upstream APIs (trusting response content without validation).
