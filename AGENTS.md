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

Documentation is part of completing every task. Follow `docs/documentation-standard.md`:
update `docs/roadmap.md` status when a numbered task advances, update
`docs/implementation-progress.md`, maintain affected subsystem READMEs and developer
guides/run instructions, and record actual verification and remaining limitations. Another
developer must be able to continue without chat history. Include documentation links in the
handoff; review documentation even for small fixes and explain when no guide changes are needed.
