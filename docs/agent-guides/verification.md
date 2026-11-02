# Verification — load for behavior changes, bugs, persistence, or integrations

## Testing strategy
- Every logic change needs proportionate, meaningful automated tests. For a pure copy/style adjustment, use the narrowest visual/smoke verification; avoid elaborate test matrices that cannot catch a realistic regression.
- Choose the cheapest trustworthy level: unit -> integration -> contract -> E2E -> startup smoke. Avoid mocking the behavior under test; mocks must respect real provider contracts.
- Cover applicable paths: nominal; boundaries; empty/missing/malformed input; original bug; rejection/error handling; serialization; state transitions; persistence/rollback; external timeouts/retries; concurrency/idempotency; backward compatibility; authorization/ownership; keyboard/accessibility for relevant UI.
- Authentication, payments, permissions, destructive flows, and data integrity need thorough positive and negative testing. Branch coverage is a signal, not a substitute for assertions.
- Never delete, weaken, skip, or broadly mock tests merely to obtain green output. Investigate flaky tests; explain if a fix is outside scope.

## Execution order
1. Reproduce the issue or identify a failing regression test where possible.
2. Add/update focused tests and run them.
3. Run the complete affected test suite, then formatter, linter, type checker, static/security checks, migrations, build, or startup checks **as applicable**.
4. Run full repo suites when shared contracts, large refactors, or deployment paths justify them and resources permit.
5. Inspect `git diff --check` and final diff for accidental churn, debug output, and secrets.

## Evidence
- Report command and outcome only for checks actually run. If blocked, specify the command, blocker, and remaining risk.
- Verify changes on supported platforms when feasible or report gaps. Startup services needed for verification should run in the foreground rather than hidden background processes.
- Do not confuse passing tests, coverage percentage, or a single successful local run with production readiness.
