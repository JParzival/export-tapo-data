# Engineering — load for architecture, refactoring, public APIs, or complex logic

## Design and scope
- Preserve the existing architecture unless a change is justified. Separate domain logic from UI, transport, persistence, and vendors where practical; respect dependency direction and avoid global mutable state or circular imports.
- Prefer explicit interfaces, typed structures, small cohesive functions, early validation, descriptive names, and simple control flow. Add abstractions only to remove meaningful coupling or duplication.
- Keep edits local. Eliminate dead code, stale flags, superseded implementations, and obsolete compatibility paths only within the task's scope. No broad opportunistic refactors or whole-file rewrites without a reason.
- For substantial architecture changes, document the decision and alternatives in an ADR or equivalent if the repo uses them.

## Refactors
- Characterize existing behavior with tests before substantial refactors.
- Separate behavioral and structural changes when possible; make incremental, reviewable patches; preserve public contracts or include a deliberate migration.
- Check affected consumers after each meaningful stage. Measure complexity or coupling only when it informs a decision.

## Documentation in code
- Document public or non-obvious modules, functions, classes, and APIs, not self-evident implementation details. Python public APIs with nontrivial parameters should use `Args:` entries for each parameter other than `self`/`cls`, including name and type; document return values, errors, side effects, invariants, security constraints, and performance considerations where meaningful.
- Prefer accurate type hints over redundant docstrings for obvious internal helpers. Explain *why* in comments, not what a line of syntax does. All code comments are in English; update stale comments and add examples for complex public APIs.
- No commented-out code, ownerless TODOs, silent failures, or unexplained placeholders. Follow existing linters, formatters, type rules, and naming standards. Treat newly introduced warnings as failures.

## Performance and dependencies
- Avoid repeated queries, unnecessary I/O, blocking inside async paths, and unbounded memory growth; paginate large results. Measure before optimizing; benchmark performance-critical work and document limits or cache behavior.
- Prefer standard library or existing dependencies. If new dependencies are justified, check active maintenance, versions, transitive risk, size, license, and runtime implications. Update lockfiles intentionally.
