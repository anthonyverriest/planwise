<typescript_web>
<code_rules>
- Validate external data (API responses, URL params, storage) at runtime with schema validation; TypeScript types are erased at build time.
- Enable strict TypeScript config: `strict: true`, `noUncheckedIndexedAccess: true`, `exactOptionalProperties: true`.
- Model domain states with discriminated unions; avoid type assertions and prefer type narrowing.
- Prefer `as const` for literal types and `satisfies` for type-safe object validation without widening.
- Follow the Rules of Hooks: call hooks at the top level only, never inside conditions or loops.
- Extract reusable logic into custom hooks; keep components focused on rendering.
- Prefer composition and render props over prop drilling; colocate state as close to its consumer as possible.
- Clean up side effects in `useEffect` return functions; use `AbortController` to cancel fetch requests and prevent race conditions.
- Derive computed values during render; reserve `useEffect` for synchronizing with external systems (subscriptions, DOM, timers), not for transforming state or props.
- Use semantic HTML elements (`nav`, `main`, `section`, `button`) over generic `div`/`span` for structure.
- Provide accessible names for all interactive elements via visible labels, `aria-label`, or `aria-labelledby`.
- Use named exports for tree-shaking; one component per file.
- Provide a unique, stable `key` on every element rendered inside a list.
- Handle all three UI states explicitly: loading, error, and success.
- Wrap subtrees with error boundaries to isolate failures; use `Suspense` with `React.lazy()` for code splitting.
- Use CSS modules or utility-first CSS; design responsive layouts mobile-first.
- Group imports: React/framework first, third-party libraries second, local modules third; remove unused imports.
- Prefer pure functions and immutable data (spread, `map`, `filter`) to minimize state-change bugs.
- Use guard clauses and early returns to flatten logic; invert conditions to reduce nesting.
- Prefer specific error types over generic ones; let errors propagate unless you can recover or add context.
</code_rules>

<constraints>
- Never use `any`, `@ts-ignore`, or `@ts-expect-error` to bypass type checking.
- Never use `as` type assertions to silence the compiler; fix the underlying type instead.
- Never use non-null assertion (`!`) on values that could genuinely be null or undefined.
- Never use `dangerouslySetInnerHTML` with unsanitized input.
- Never use `eval()`, `Function()`, or `innerHTML` with dynamic content.
- Never store secrets, tokens, or PII in client-side code or localStorage.
- Never block the main thread with synchronous heavy computation; offload to Web Workers or break into smaller async chunks.
- Never use array index as `key` for dynamic lists that can reorder, insert, or delete items.
- Never mutate state directly; always use the setter from `useState` or an immutable update pattern.
- Never call hooks conditionally or inside loops; follow the Rules of Hooks.
- Never ignore the exhaustive-deps lint rule; fix the dependency array or restructure the effect.
- Never use `useEffect` to compute state that can be derived from existing state or props during render.
- Never use deprecated React APIs or legacy patterns (class components, string refs, `findDOMNode`, `UNSAFE_` lifecycle methods).
- Never use inline styles for layout or theming; use CSS modules, utility classes, or design tokens.
- Never suppress accessibility warnings without documented justification.
</constraints>
</typescript_web>