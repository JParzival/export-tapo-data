# AGENTS.md — Efficient, Reliable Engineering

## Goal and precedence
Deliver correct, secure, maintainable, tested changes consistent with the repo. Follow user/system instructions, applicable nested `AGENTS.md` files, and existing project conventions. Resolve conflicts before risky or irreversible changes. Never trade correctness for speed or fewer tokens.

## Project context
- The project provides an experimental Tkinter desktop application and a Python console prototype for requesting Tapo sensor exports. Automatic attachment downloads are not implemented; future distribution and additional features require user requirements rather than assumptions.
- The user reports successful real-account login, sensor discovery, export, and email receipt of a correctly exported file through the desktop app. This confirms the tested case, not all sensors, date ranges, or provider behavior. Local mocks do not establish the provider's behavior.
- The integration uses an unofficial, potentially changing API and a locally verified Tapo APK. Preserve credential and token confidentiality, avoid duplicate export requests, and document dependencies and validation limits. Do not perform real requests or handle personal sensor data without the user's authorization.
- Before staging or publishing, review all proposed files and the staged diff for secrets, personal information, local paths, sensor exports, and third-party material. Ignore rules are a safeguard, not proof that a file is safe to publish; never force-add sensitive files.
- Keep the existing console scripts usable while building the application unless a change is explicitly agreed. Update the project documentation as requirements and real-world validation become known.

## Context and search (progressive disclosure)
1. Check `git status --short`; preserve unrelated work. Identify the likely component from the request and repo manifests/tree; don't map the whole repo by default.
2. Find paths first: `rg --files <likely-dir> -g '<glob>'`; then filenames (`rg -l`), then exact symbols (`rg -n -F '<symbol>' <scope>`). Use bounded context (`rg -n -C 5`), opening only relevant functions and nearby tests. Prefer indexed language tools when available.
3. Search the narrowest likely directory/file; broaden to adjacent modules, then the repo only if results or call sites require it. Exclude generated/vendor/build files. Limit command output; never dump huge files, logs, or search hits.
4. Reuse discovered paths and prior outputs; do not repeat unchanged searches or reread entire files. Check call sites, tests, interfaces, and applicable nested instructions before editing.
5. Inspect external docs or dependencies only when repository evidence cannot answer the question or current compatibility/security requires it. Don't add tools solely for browsing code.

## Work and communication
- For a small fix: investigate -> patch -> focused check. For cross-module/high-risk work: very briefly outline approach, dependencies, risks, and verification first.
- Reproduce bugs where practical; fix causes, not symptoms. Keep edits minimal, cohesive, and reviewable. Preserve behavior and public contracts unless the task explicitly changes them.
- Short updates only when strictly needed; never narrate routine searches. In responses, give short conclusions rather than repetitive reasoning, full file contents, or raw command dumps.
- Final report defaults to 3 concise items: **Changed**, **Verified** (actual commands/results), **Risks/next actions** (only if applicable). Expand for complex or unsafe changes. Never claim tests ran if they did not.

## Engineering invariants
- Respect boundaries and dependency direction. Prefer simple, typed, explicit, testable code; avoid hidden state, circular imports, speculative abstractions, unused paths, silent errors, and unrelated refactors.
- Follow formatter, lint, typing, naming, and existing conventions. Document non-obvious behavior and public contracts; code comments in English; preserve UTF-8 (prefer no BOM).
- Validate untrusted inputs at boundaries. Protect secrets, personal data, authorization, ownership, and destructive actions. Never log or commit sensitive data; never disable controls to make tests pass.
- Do not overwrite user changes, run destructive Git operations, or add dependencies without assessing necessity, compatibility, maintenance, license, security, and lockfile impact.
- Add meaningful tests for changed logic (normal, boundary, failure, regression as relevant). Never weaken/skip tests to claim success. Keep docs/configuration in sync only when affected.
- Verify in increasing scope: relevant test(s) -> affected suite -> broader checks only when warranted; use formatter/lint/types/build/security/migration checks according to risk; review diff and `git diff --check` when practical. Report unrun checks and residual risk.
- Network calls need bounded timeouts; retries only for transient, safe/idempotent operations. Avoid unbounded I/O; benchmark before optimizing.

## Risk-aware reference rules — open only if relevant
- Architectural changes, refactoring, APIs, Python docstrings, or complex logic: `docs/agent-guides/engineering.md`.
- Nontrivial behavior changes, bugs, persistence, integrations, or test strategy: `docs/agent-guides/verification.md`.
- Authentication, sensitive data, external providers, dependencies, schemas, migrations, or deployment: `docs/agent-guides/security-operations.md`.
- Frontend, accessibility, UX, or user-visible states: `docs/agent-guides/frontend.md`.
Do not preload every guide. Read the applicable guide(s) before implementing their category; nested repository instructions still apply.

## Done
Requested behavior works; affected contracts stay valid; relevant tests/checks pass; no unrelated churn, secrets, debug artifacts, or unjustified TODOs. Document blocked verification and required user actions. For larger changes, summarize key files and trade-offs.
