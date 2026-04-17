<rust_web>
<code_rules>
- Use `Drop` and RAII for resource cleanup (file handles, locks, connections).
- Tokio channels: prefer bounded `mpsc`/`broadcast`/`watch`/`oneshot` over shared state—unbounded channels are silent OOM risks under backpressure. Use `Arc<tokio::sync::Mutex<T>>` or `Arc<tokio::sync::RwLock<T>>` only as a last resort; `Arc::clone` is cheap but atomic ref-count overhead compounds under contention. Never hold any lock across an `.await` point. Never use `std::sync::Mutex` in async code paths.
- Tokio task lifecycle: use `JoinSet` for coordinated tasks, `tokio_util::task::TaskTracker` for fire-and-forget tracking. Ensure every spawned task has a clear shutdown path via `CancellationToken` or `tokio::select!`. Handle OS signals (`SIGTERM`/`SIGINT`) and drain in-flight work in dependency order before exit. Use `Semaphore` to bound parallelism. Use `spawn_blocking` for synchronous/CPU-heavy work.
- Cancel-safety: all `select!` branches must be cancel-safe (`write_all`, `read_exact`, `Mutex::lock` are NOT—pin long-lived futures outside the select loop).
- Use `serde` with `#[derive(Deserialize, Serialize)]` and `serde_valid` for structured data validation. Use `#[serde(deny_unknown_fields)]` on types deserializing untrusted input. Use `#[serde(borrow)]` with `&'de str`/`Cow<'de, str>` for zero-copy deserialization on hot paths.
- Use `sqlx::query!`/`query_as!` with string literal SQL for compile-time checking. Use `QueryBuilder` for dynamic SQL. Use `SQLX_OFFLINE=true` with `.sqlx/` prepared queries for CI. Explicitly `commit()` or `rollback()` transactions—do not rely on `Drop` implicit rollback.
- Design small, focused modules and crates named by what they provide; no `util`/`common`/`helpers` modules.
- Define enums with named variants and implement `Display` for debuggability—use `write!()` directly in `fmt`, never `format!()`. Derive `Debug` on all public types. Match all variants explicitly—never use `_ =>` on enums you control (new variants must be compile errors, not silent swallows). Prefer enums over booleans for function parameters (`Mode::Strict` over `true`).
- Run `clippy` with `-D warnings`; `rustfmt` and `clippy` are enforced by pre-commit hooks.
- Use guard clauses and early returns to flatten logic; invert conditions to reduce nesting.
- Verify invariants and pre/postconditions with explicit checks; return `Result` for recoverable errors, use `panic!` only for truly unrecoverable programmer bugs. Use `Result` returns (not `panic!`) for validation at public API boundaries.
- Pre-allocate collections with `Vec::with_capacity`/`HashMap::with_capacity` when size is known or estimable—avoid realloc cascades. Prefer lazy iterator chains (`.iter().map().filter()`) over collecting into intermediate `Vec`s then re-iterating.
- Prefer pure functions and owned/borrowed value types to minimize state-change bugs.
- Prefer composition; use traits for polymorphism.
- Return errors explicitly using `Result<T, E>`; define domain error enums with `thiserror` and use `anyhow` at application boundaries for context. Match errors with pattern matching, never string comparison.
- Handle errors at the call site; don't propagate with `?` without adding context via `.context()` or `.map_err()`.
- Use `pub(crate)` or private visibility for internal APIs; minimize public surface area.
- Accept trait bounds, return concrete types: depend on behavior, not implementation. Prefer `&str` over `&String`, `&[T]` over `&Vec<T>` in signatures. Never allocate `String`/`format!`/`.to_string()` when a `&str` borrow or write to an existing buffer suffices. Program to `Read`/`Write`/`AsyncRead`/`AsyncWrite` traits for composable stream processing.
- Use the builder pattern or `Default` + field overrides for configurable constructors; implement `Default` so the default instance is a valid, ready-to-use state.
- Pass `&T` for reads, `&mut T` for mutation, owned `T` when callee needs ownership. Prefer stack > borrow > `Cow` > owned clone > `Arc` > `Box<dyn Trait>`—escalate only when the type system demands it. Never `.clone()` when a borrow suffices; when cloning is necessary, prefer cheap handle clones (`Arc::clone(&x)`) over deep copies. Use `Cow<'_, T>` to defer cloning until mutation is needed. Never clone to satisfy the borrow checker without understanding the ownership issue. Never capture non-`'static` references in spawned tasks; move owned data in. Never use `Rc`/`RefCell` in async or multi-threaded code.
- Prefer `impl Trait` in return position over `Box<dyn Trait>` for single-type returns (iterators, futures). Use `Box<T>` only for recursive types, large stack values, or single-owner trait objects—never as a default. Use `async fn` in traits directly; add `Send` bound on the trait when futures must be spawned.
- Keep lifetime annotations minimal: rely on elision rules; add explicit `'a` only when the compiler requires it or when it clarifies the borrow relationship to the reader. Never introduce self-referential structs—use indices, keys, or `Arc` instead.
- Axum 0.8 path syntax: use `/{param}` and `/{*rest}`, not `:param` or `*rest`. `Option<T>` extractors require `T: OptionalFromRequestParts`. Body-consuming extractors (`Json<T>`, `Form<T>`) must be the last handler argument; `FromRequestParts` extractors (e.g., `State`, `Path`) come first. Do not use `#[async_trait]` on `FromRequest`/`FromRequestParts` impls—Axum 0.8 uses native async traits.
- Rust 2024 edition: `unsafe_op_in_unsafe_fn` warns by default—wrap individual unsafe ops in `unsafe {}` blocks inside `unsafe fn`. Use `use<'a, T>` precise capturing syntax for RPIT when needed. `gen` is a reserved keyword. Use let chains in `if`/`while` conditions to flatten logic.
- Prefer `async || {}` closures (stable since 1.85) over `|| async {}` when the closure captures by reference—async closures have correct lifetime semantics.
- Tower middleware order (outermost to innermost): set-request-id → body-limit → trace → CORS → rate-limit → timeout → auth → idempotency → service. Use `backon` for ergonomic retry with exponential backoff and jitter at adapter boundaries.
</code_rules>

<constraints>
- Never silently ignore errors with `let _ =`; always handle or explicitly document why it's safe to discard. Use `#[must_use]` on types and functions where ignoring the return value is a bug.
- Never use wildcard imports (`use module::*`) except for preludes.
- Never use `unsafe` blocks unless absolutely necessary and justified with a `// SAFETY:` comment.
- Never create circular module dependencies; break cycles by extracting shared types into a common module or using traits.
- Never use temporal language in naming ('improved', 'new') or comments ('recently refactored'). All code must be evergreen.
- Never use global mutable state (`static mut`, lazy `Mutex` globals); prefer dependency injection.
- Never make a function `async` that never `.await`s—each `async fn` generates a state machine; use synchronous signatures when no suspension point exists.
- Never put complex logic in `build.rs` or proc macros; prefer explicit initialization for testability and clear dependency order.
</constraints>
</rust_web>