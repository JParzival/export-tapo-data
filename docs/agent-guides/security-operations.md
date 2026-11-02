# Security and Operations — load for data, trust boundaries, providers, and deployment

## API/data contracts
- Validate and normalize external input at boundaries. Return stable structured errors without leaking internal traces, secrets, or provider payloads.
- Preserve backward compatibility unless a breaking change is approved; version affected public APIs. Test serialization, nullability, defaults, validation, and constraints.
- Schema changes require deliberate migrations and rollback paths, or explicit documentation of irreversibility. Consider ownership, isolation, and data retention.

## Security/privacy
- Keep tokens, credentials, private keys, and real production data out of the repo, examples, and logs. Use project secret handling or environment configuration.
- Use least privilege, deny-by-default authorization, tenant/ownership checks, safe provider identifiers, and controlled destructive/costly actions.
- Evaluate relevant risks: injection, path traversal, SSRF, XSS, CSRF, replay, unsafe uploads, insecure deserialization, dependency vulnerabilities, sensitive logging. Add regression tests at affected trust boundaries.

## Reliability
- Make failures observable, with actionable context but no sensitive content. Set bounded timeouts. Retry only transient idempotent operations with capped backoff; protect mutations from duplicate execution.
- Preserve transactional integrity; use compensating actions where required. Add structured logs, metrics, traces, audit events, or health checks where operational impact warrants them.

## Deployment/config/docs
- Use safe local defaults, validate startup configuration, and distinguish dev/test/staging/prod. Document new variables in `.env.example` without secrets. Ignore generated artifacts, caches, databases, and credentials in Git.
- Update README, API docs, environment/deployment guides, ADRs, migrations, troubleshooting, or changelog **only where behavior, operation, or contracts change**. Document commands with their working directory and expected result; include recovery and security implications when relevant.
- Do not run destructive commands or modify unrelated workspace changes. Perform an explicit secret/diff review before completion.
