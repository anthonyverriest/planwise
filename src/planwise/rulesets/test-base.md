<test_base>
<code_rules>
- Maximize signal density: optimize signal-to-noise ratio, eliminate redundancy and noise.
- Write idiomatic code: follow language conventions naturally, enable local reasoning.
- Make code self-explanatory: use descriptive names that reveal intent (avoid abbreviations, single letters except iterators).
- Use clear visual separation: two blank lines between top-level definitions (functions, classes); one blank line between methods.
- Every functional test has a doc comment `Contract: [behavior locked down]`.
- Every adversarial test has a doc comment `Hypothesis: [what you expect to break and why]`.
- Test names describe the contract or hypothesis (e.g., `create_member_returns_member_with_defaults`, `auth_rejects_token_with_future_iat`).
- Each test verifies one contract or one hypothesis — no multi-purpose tests.
- Reuse existing helpers, fixtures, and factories instead of duplicating test infrastructure.
- New helpers added by tests live in the test file's local scope, not in shared infrastructure.
- Use the project's existing assertion patterns with descriptive messages.
- Group tests by type or dimension using the project's comment syntax.
- Mocks must reflect actual API responses including all fields downstream code uses.
- Concurrency tests use synchronization primitives and assert deterministic outcomes — never sleep-based timing.
- Tests are deterministic and order-independent.
- If a test exposes a real bug, document it via the test — do not fix it from the test workflow.
</code_rules>

<constraints>
- Never sacrifice correctness or clarity for brevity.
- Never do scope creep or drive-by refactors.
- Never use magic numbers or hardcoded strings; use named constants.
- Never add complexity without measurable benefit.
- Never log credentials, tokens, or PII.
- Never include inline comments (code must be self-explanatory). Exception: inherently complex logic.
- Never use deprecated functions or APIs.
- Never use temporal language in naming ('improved', 'new') or comments ('recently refactored'). All code must be evergreen.
- Never modify production code from a test workflow.
- Never add test-only methods or properties to production code.
- Never write tests that depend on execution order or shared mutable state.
- Never silently mark a failing test as passing.
</constraints>
</test_base>
