# Optimize — Dimension analysis protocol

This file is read by subagents spawned from `optimize.md`. Main thread does NOT read it.

**Evaluator lock:** Do NOT modify test files or test fixtures (e.g., `tests/`, `__tests__/`, `*_test.*`, `*.spec.*`, and any test helper/fixture files). If a change breaks tests, the change is wrong — not the tests.

## Dimension analysis

Adopt the dimension named in your input. Stay strictly within that lens — items in the dimension's "out of scope" list belong to other agents and must not be reported here. Rules (passed in your input) are not a discovery source; they constrain how fixes are written, not what to find.

Look up your dimension's lens question, "what this lens reveals" list, and "out of scope" list in § **Dimensions** below.

Report BOTH:
- **Findings** — problems to fix (issues, violations, bugs).
- **Proposals** — opportunities to evolve (ways to make good code better). Only propose changes you are confident improve the code. No speculative "might help" proposals.

If your input includes a prior ledger, skipped set, or failed set: do not re-report items already present. If a challenge context is provided, focus on the files and gaps the challenger identified.

Max 2 Explore subagents.

### Return contract

```
## Findings (problems to fix)
### [CRITICAL | HIGH | MEDIUM] Title
**Location:** @path:line
**Narrative:** [what is wrong, why it matters under this lens]

## Proposals (opportunities to evolve)
### Title
**Location:** @path:line
**Hypothesis:** [one-line why this improves the code]
**Concrete change:** [what to do]
**Expected impact:** [simpler | faster | safer | more accessible — be specific]
```

## Dimensions

### Dimension 1: Safety
**Lens question:** "Where could this fail unexpectedly or be exploited?"

**What this lens reveals:**
- Missing input validation at system boundaries; trust assumptions that don't hold
- Edge cases (empty/None, boundary values, off-by-one, integer overflow)
- Race conditions, missing locks, unsafe shared state, unawaited coroutines, swallowed cancellation
- Swallowed or lost errors, bare excepts, inconsistent error semantics across call sites
- Resource leaks (file handles, sockets, connections, locks held outside context managers)
- Injection surfaces (SQL, shell, template, deserialization), secret/PII leakage in logs or errors
- Deprecated APIs with known security or correctness issues

**Out of scope for this lens:**
- Style and readability → Quality
- Module-level coupling → Structure
- Algorithmic cost → Performance

### Dimension 2: Quality
**Lens question:** "Could a new contributor read this in 5 minutes and understand intent?"

**What this lens reveals:**
- Cognitive complexity (deep nesting × control flow breaks — functions hard to reason about)
- Code smells (long method, large class, feature envy, data clumps, primitive obsession)
- Low signal density (verbose wrappers, redundant boilerplate, patterns that obscure intent)
- Duplication and near-duplicates differing only in names/constants
- Missing or leaky abstractions (logic that belongs in a shared function/class)
- Dead code (unreachable branches, unused imports/variables/functions, stale feature flags)
- Magic numbers and hardcoded strings scattered through logic
- Naming inconsistencies (same concept under different names; names that don't match behavior)
- Pattern inconsistencies (same operation implemented differently across call sites — the outlier is usually the drift; align to the majority pattern unless the majority is wrong)
- Convention violations relative to surrounding code or project rules

**Out of scope for this lens:**
- Module boundaries and inter-file structure → Structure
- Runtime cost of patterns → Performance
- Bugs that only fire in edge cases → Safety

### Dimension 3: Structure
**Lens question:** "If a likely future change lands here, how many files would have to move?"

**What this lens reveals:**
- Layering violations (domain logic in infrastructure; infrastructure in handlers)
- Circular or unnecessary dependencies between modules
- Change coupling (files that always change together reveal hidden dependencies)
- Afferent/efferent coupling extremes (too many dependents = fragile; too many dependencies = unstable)
- Low cohesion (classes/modules with split responsibilities — high LCOM)
- Connascence (shared assumptions between modules that make changes ripple)
- God classes/modules with too many responsibilities
- Missing or misplaced boundaries (logic that should live behind an interface/protocol)
- Coupling to concrete implementations where abstraction is warranted
- Deep inheritance hierarchies where composition is simpler
- Observability gaps at architectural boundaries (missing structured logging, metrics, tracing)

**Out of scope for this lens:**
- Within-function complexity → Quality
- Error handling correctness → Safety
- Latency or throughput characteristics → Performance

### Dimension 4: Performance
**Lens question:** "What's the hot path doing that it shouldn't?"

**What this lens reveals:**
- Hot paths with unnecessary allocations or copies
- Missing or incorrect caching (stale cache, unbounded growth, invalidation gaps)
- Suboptimal concurrency (event loop blocked by sync I/O, missing parallelism for independent I/O)
- O(n²) or worse algorithms where O(n log n) or O(n) alternatives exist
- Unnecessary serialization/deserialization round-trips
- Database query patterns (N+1 queries, missing indexes implied by patterns, unbounded result sets)
- Wasted I/O (reading the same file/key multiple times in one operation)

**Out of scope for this lens:**
- Resource leaks (correctness concern) → Safety
- Code duplication → Quality
- Module coupling → Structure
