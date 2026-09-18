# Tests

- `tests/unit/` — domain and helper tests
- `tests/api/` — FastAPI route tests
- `tests/integration/` — Postgres, LocalStack S3, and selected Celery/Redis processing tests

```bash
source .venv/bin/activate
pytest
```

Pytest needs a filled-in `.env` at the repo root locally. GitHub Actions sets `CI=true` and supplies the same keys as job environment variables instead.

Use development services, apply migrations, and inspect skips with `pytest -ra`. Missing
services/schema can skip integration tests; a passing run with skips is not full integration
coverage. Current CI starts Postgres but not Redis or LocalStack. See the
[runbook](../docs/development-runbook.md) for commands, prerequisites, and manual review steps.

Retrieval tests cover domain query validation, API identity/schemas/errors, provider output
validation, and real Postgres vector/FTS isolation, source changes, partial state, and neighbors.
Ordinary pytest does not call live model APIs. The separate [retrieval eval](../evals/retrieval.py)
provides offline ranking baselines and an opt-in synthetic live-provider check; see the
[verification limits](../docs/document-retrieval.md#verification-and-manual-review).

4.5 adds grader mutation tests (`test_manual_eval.py`) and a database cleanup test
(`test_manual_eval_cleanup.py`) that deliberately fails inside the corpus transaction.
The independent `python -m evals.manuals` command is a CI gate using real PostgreSQL and
recorded provider responses; missing prerequisites fail rather than skip that command.
See the [manual eval guide](../docs/manual-evaluations.md).

Conversation tests (`test_conversations.py`, `test_conversations_http.py`,
`test_conversation_repository.py`) cover ownership, bike-context boundaries, rolling-summary
refresh, and delete cascades. Apply migration `0014_conversations` before the integration case.
Compact-context tests (`test_compact_context.py`, `test_compact_context_http.py`) cover pack
shape, turn budgets, deferred domain stubs, and owner isolation.
