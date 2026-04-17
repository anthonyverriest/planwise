<base>
<code_rules>
- Maximize signal density: optimize signal-to-noise ratio, eliminate redundancy and noise.
- Write idiomatic code: follow language conventions naturally, enable local reasoning.
- Fail-fast: validate inputs at boundaries, detect errors early.
- Add concise docstrings (file-level: what it does, make greppable; function-level: Google-style purpose and behavior).
- Make code self-explanatory: use descriptive names that reveal intent (avoid abbreviations, single letters except iterators).
- Log key decision points and state transitions at architectural boundaries for traceability and debugging.
- Use clear visual separation: two blank lines between top-level definitions (functions, classes); one blank line between methods.
</code_rules>

<constraints>
- Never sacrifice correctness or clarity for brevity.
- Never do scope creep or drive-by refactors.
- Never skip edge case handling or input validation at boundaries.
- Never use magic numbers or hardcoded strings; use named constants.
- Never add complexity without measurable benefit.
- Never log credentials, tokens, or PII.
- Never include inline comments (code must be self-explanatory). Exception: inherently complex logic.
- Never use deprecated functions or APIs.
- Never use temporal language in naming ('improved', 'new') or comments ('recently refactored'). All code must be evergreen.
</constraints>
</base>