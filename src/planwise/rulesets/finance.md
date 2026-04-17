<finance_engineering>
- Idempotency & Consumers: All state-mutating operations and queue consumers MUST be idempotent to support at-least-once delivery. Require client-supplied idempotency keys at the API boundary and validate them before processing.
- Distributed Consistency (Outbox): Never dual-write to a database and a message queue. Use the Transactional Outbox pattern to atomically persist state changes and outbound events.
- External State Ambiguity: When an external exchange API times out or returns a 5xx response, treat the resulting state as UNKNOWN. Do not blindly retry. First query the exchange using the client order ID to determine the actual state.
- Reconciliation: Local state and external exchange state will drift. Implement reconciliation routines that periodically verify balances and order statuses against the exchange's source of truth.
- Precision: Never use floating-point types for monetary values. Use integer types denominated in the smallest currency unit, or a fixed-precision decimal type. Use checked arithmetic — never allow silent overflow or truncation. Define domain types (e.g., `Satoshis`, `Cents`) to prevent unit mixing.
- Immutability & Auditability: Financial records are append-only. Do not modify balances or positions without an auditable trail such as ledger entries or recorded domain events.
- Concurrency & ACID: Protect balance mutations from race conditions using pessimistic locking or optimistic versioning. Multi-step local database operations must be atomic. Use advisory locks for cross-process coordination on shared resources.
- Resiliency & Limits: Enforce exchange rate limits and use bounded retries with exponential backoff and jitter at external boundaries.
- Fail-Closed & Invariants: When state cannot be verified, fail closed and prevent further processing until reconciliation completes. Continuously verify critical accounting and risk invariants.
- Determinism: System behavior must be deterministic. Inject time and randomness through abstractions. Design events so they can be replayed deterministically in shadow and audit environments.
- Supply Chain: Audit dependencies for known vulnerabilities, license restrictions, and supply chain risks before adding new packages.
</finance_engineering>
