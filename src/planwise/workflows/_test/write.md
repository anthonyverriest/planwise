# Test — Test-writing protocols

This file is read by subagents spawned from `test.md`. Main thread does NOT read it.

Follow the Rules passed in your input (docstrings, naming, helper reuse, production code lock, deterministic concurrency tests, etc.). Language rules govern your test scaffolding — adversarial payloads fed into production code under test are unconstrained by them.

Follow the project's existing test patterns for setup, assertions, and async handling.

**Production code lock:** Do NOT modify any non-test files. If the code under test has a real bug, document it in BLOCKED — do not fix it.

## Functional tests

Write tests covering the provided functional test cases (ordered by type).

### Return contract (functional)

```
WRITTEN: [test count] tests in [file]
SKIPPED: [count] (not feasible without infrastructure changes)
BLOCKED: [describe what prevents writing the test]
```

## Adversarial tests

Write tests covering the provided attack vectors (ordered by severity). Max 8 vectors per agent dispatch.

After writing each test:
1. State what you expect: PASS (code handles it correctly) or FAIL (test exposes a bug).
2. If you expect FAIL, explain the bug the test would expose.

### Return contract (adversarial)

```
WRITTEN: [test count] tests in [file]
EXPECTED_PASS: [count] (code is robust)
EXPECTED_FAIL: [count] (potential bugs found)
SKIPPED: [count] (not feasible without infrastructure changes)
BLOCKED: [describe what prevents writing the test — missing fixture, unclear behavior, production code needs changes]
```
