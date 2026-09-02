# Vroometr Agent Instructions

Read the relevant files in `docs/design/` before making product or architectural decisions.

Decisions marked LOCKED are the source of truth.

Core backend architecture:

`route -> domain service -> repository -> database`

AI architecture:

`agent -> tool -> same domain service -> repository -> database`

Do not invent mechanical specifications.

Do not bypass backend authorization.

Do not introduce new infrastructure or replace locked architecture without explicit approval.

Important config (passwords, keys, hosts, ports, buckets, model names) lives in `.env`, not hardcoded. `.env.example` lists key names only — no values.

Keep changes small, tested, and focused.
