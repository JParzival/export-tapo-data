# Frontend — load for UI, accessibility, or user-facing interactions

- Follow existing UI architecture and design system; keep component/state changes localized.
- Maintain semantic HTML, accessible labels, keyboard support, logical focus, and visible focus indicators.
- Handle loading, empty, partial, error, success, disabled, and retry states where appropriate. Avoid duplicate submissions.
- Keep responsive layouts and meaningful error messages; do not expose internal diagnostics to end users.
- Protect destructive actions with clear confirmation and recovery behavior.
- Test affected interactions and accessibility contracts; for simple copy/CSS changes, use focused smoke/visual checks rather than unrelated suites.
- Keep user-facing text consistent with project localization; code comments remain in English.
