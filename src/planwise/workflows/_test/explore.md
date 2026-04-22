# Test — Infrastructure exploration protocol

This file is read by subagents spawned from `test.md`. Main thread does NOT read it.

## Test infrastructure exploration

Map the project's test infrastructure relevant to the target.

Find and read:
- Shared test helpers, fixtures, factories, builders
- Request/response utilities and test clients
- Conftest files, setup/teardown patterns
- Existing tests for the target files (or similar modules)
- Available test dependencies (property-based testing libs, faker, etc.)

## Return contract

Report:
- Reusable helpers with their signatures and import paths
- Assertion patterns and conventions used in existing tests
- What test types are supported (unit, integration, async, concurrency)
- Available fixture/factory patterns with code snippets
- Test infrastructure gaps — what CAN'T be tested with current tooling
