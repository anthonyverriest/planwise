<python>
<code_rules>
- Use context managers (`with` statements) for resource management; use `async with` for async resources.
- Choose concurrency model based on workload: asyncio for I/O-bound, multiprocessing for CPU-bound.
- Use Pydantic v2 models to define and validate structured data.
- Place all imports at top of file; remove unused imports.
- Follow PEP 8 best practices.
- Use guard clauses and early returns to flatten logic; invert conditions to reduce nesting.
- Apply Python 3 static typing using PEP 585.
- Use asserts extensively for catching bugs (verify invariants, pre/postconditions); they're development-time checks, not runtime guarantees. Use raise (not assert) for input validation at public API boundaries.
- Prefer pure functions and immutable data structures to minimize state-change bugs.
- Prioritize vectorized operations over explicit loops for numerical data.
- Prefer composition over inheritance.
- Prefer specific exceptions over generic ones; let exceptions propagate unless you can recover or add context.
- Minimize try/except scope: wrap only operations that raise exceptions, not entire function bodies.
- Mark internal APIs with single leading underscore.
</code_rules>

<constraints>
- Never use bare `except:` clauses; always specify exception types.
- Never block the event loop in async functions; use asyncio.to_thread() for blocking calls.
- Never swallow asyncio.CancelledError; propagate after cleanup (use try-finally).
- Never use wildcard imports (`from module import *`).
- Never use inline imports. Exception: optional dependency imports guarded by try/except.
- Never use `eval()` or `exec()` on untrusted input.
- Never create circular import dependencies; break cycles by extracting shared types into a common module or using Protocol for structural typing.
- Never use `global` variables or `TYPE_CHECKING` blocks.
</constraints>
</python>
