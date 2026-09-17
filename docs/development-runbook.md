# Development runbook

Use alongside the [implementation guide](developer-guide.md). Commands below start from the
repository root unless a `cd` is shown. Use a development database/bucket for tests; some
integration fixtures commit temporary records and perform object deletion during cleanup.

## First checkout

Requirements: Python 3.12 or later, Node.js 22 (matching CI), npm, Docker with Compose,
and development Clerk configuration. Obtain the ignored design files from the project owner
before product or architecture work. Do not copy somebody else's real secrets into Git.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env` using the key catalog and the project's development configuration. Copy only when
creating a new file; preserve an existing `.env`. Python dependencies include PyMuPDF for PDF
preflight. OpenAI embeddings and reranking are implemented; other model adapters remain unconfigured. See
[embedding setup](document-indexing.md#configuration) and [search setup](document-retrieval.md#configuration-and-migration).
Search also requires `RERANKER_MODEL` and the required `RERANKER_TIMEOUT_SECONDS` in root `.env`.

Configuration groups:

| Purpose | Configuration source |
| --- | --- |
| Postgres connection | `POSTGRES_*` keys |
| Queue and retry lease | `REDIS_URL`, `CELERY_LOG_LEVEL`, `PROCESSING_LEASE_SECONDS` |
| Object storage | `AWS_*`, `S3_BUCKET` |
| API listener / web-to-API connection | `API_HOST`, `API_PORT`, `API_URL` |
| Clerk verification and web session | `CLERK_*`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` |
| Feature flags | `FLAGS_PROVIDER`, `UNLEASH_*` |
| Embeddings | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_VERSION`, `EMBEDDING_TIMEOUT_SECONDS` |
| Future model adapters | Remaining model keys listed in `.env.example` |

Use `.env.example` for the complete current list. Values, including hosts, ports, buckets, and
model names, belong in environment configuration. The web launcher loads root `.env`; Next.js
also reads `apps/web/.env.local` when present. Check both when web and API settings disagree.

```bash
./scripts/dev-up.sh
./scripts/compose.sh ps
cd services/api
alembic upgrade head
alembic current
cd ../..
cd apps/web
npm ci
cd ../..
```

Current schema head is `0013_retrieval_fts`. `dev-up.sh` starts the existing local services and
ensures the Unleash database exists. LocalStack startup initializes the configured private S3
bucket. See [infrastructure details](../infra/README.md).

## Run the application

Use separate terminals, activating `.venv` for Python processes:

```bash
./scripts/api-dev.sh
```

```bash
./scripts/worker-dev.sh
```

```bash
./scripts/web-dev.sh
```

Use the configured API/web addresses. API diagnostics are `/health/live`, `/health/ready`,
and `/health/deps`; readiness requires Postgres, while dependency diagnostics inspect additional
stores. FastAPI's `/docs` exposes exact request/response schemas. Sign in through the web app
to exercise owner-authenticated flows. Health success alone does not verify Clerk, file uploads,
or worker execution.

Use the launchers: API and worker need repository, shared-library, and API import paths.
Fully restart processes after launcher/env/dependency changes; code reload does not replace
the inherited environment. Run migrations before exercising newly added endpoints.

## Checks

From an activated Python environment at the root:

```bash
ruff check libs tests services/api workers pipelines evals
pytest -ra
PYTHONPATH=libs:services/api python -m evals.chunking
PYTHONPATH=libs:services/api python -m evals.retrieval
PYTHONPATH=libs:services/api python -m evals.manuals
git diff --check
```

For web changes:

```bash
cd apps/web
npm run lint
npx tsc --noEmit
npm run build
```

Some restricted development environments prevent Turbopack from binding a required port.
`npm run build -- --webpack` has been used successfully as an explicit fallback; record which
build was run. Font downloads can require network access during a build.

Unit tests cover services and helper behavior; API tests exercise schemas/auth/error mapping;
integration tests exercise real Postgres, S3, and selected Celery/Redis behavior. Missing services
or migrations can cause integration skips. Read the skipped-test report before claiming complete
coverage. Tests use in-memory feature flags, not a live Unleash connection.

CI runs Python lint/tests with Postgres, web lint/build, and Docker image builds. Redis and
LocalStack are not started by the current workflow, and CI does not deploy. Review the actual
[workflow](../.github/workflows/ci.yml) when changing prerequisites.

The last 4.1 implementation verification recorded 187 Python passes and five PyMuPDF/SWIG
deprecation warnings. This is historical evidence, not a guarantee about a new checkout.
The prior isolated Chrome harness used the actual document component with mocked APIs and
temporary files outside the repository; it is not a checked-in, reproducible browser test suite.

## Manual smoke review

1. Sign in, create a combustion bike and an electric bike, and confirm the correct fields are
   required. Switch active bikes, refresh, then archive the selected bike and check fallback.
2. Open Documents, upload a small PDF, verify its bike link, then view/download it. Inspect
   pooled usage. Unlink it and find it under Show all account files; relink without reuploading.
3. With the worker running, observe queued/running checks becoming finished/not scanned.
   Use Run checks or Retry checks on existing files. This does not validate malware detection.
4. Register the PDF, correct metadata, and confirm. Upload another copy to exercise duplicate
   warnings; select an edition predecessor and confirm. Check archiving and primary override.
5. On a confirmed document, choose Extract pages with the worker running. Review the original
   page numbers and text; visual pages should say provider pending. Retry incomplete pages.
   Native text pages already completed should remain available.
6. Choose Build sections & embeddings. Review hierarchy, chunk source pages/offsets, and
   embedding status. Without credentials, sections should persist with an explicit configuration
   message. Re-extract pages and confirm the old index is marked stale.
7. Search a phrase in an indexed PDF. Verify exact text/page citations and View source PDF.
   Include reference editions explicitly; switch bikes and confirm results clear. Try absent
   information and unavailable providers. See the [retrieval review](document-retrieval.md#verification-and-manual-review).
8. Try an encrypted PDF and confirm registration fails visibly. Switch bikes/accounts to check
   isolation. After the upload grant expires, review and confirm file deletion and quota cleanup.

## Troubleshooting

| Symptom | Inspect / next action |
| --- | --- |
| Settings fail at import | Root `.env` and required keys in `libs/vroometr/settings.py`; never dump secret values into logs |
| Database unavailable / missing relation | `./scripts/compose.sh ps`, configured connection, `alembic current`, then apply pending migrations |
| Sign-in works but API returns 401 | Clerk JWT verification settings, authorized party, web `API_URL`, and server env consistency |
| Upload fails in browser | LocalStack availability/bucket initialization, configured endpoint reachability from the browser, signed policy and CORS |
| Could not start background checks | Redis availability, API logs, launcher import paths; fully restart API using `api-dev.sh`, then retry |
| Checks stay queued/running | Worker logs and task registration; retry once the displayed lease expires |
| Checks finished / Not scanned | Expected unconfigured scanner behavior; a worker restart will not install a scanner |
| Delete temporarily blocked | Wait until `deletable_after`; the upload grant is still valid |
| File changed during document confirmation | Stored bytes no longer match registration hash; register an unchanged copy |
| PDF registration rejected | Use an unlocked, valid nonempty PDF; images remain file attachments |

To stop local services, run `./scripts/dev-down.sh`. Do not remove Docker volumes as routine
troubleshooting; doing so loses local data. Production rollout, backup/restore, and automatic
processing reconciliation are not implemented runbooks yet.

## Manual evidence evals

`python -m evals.manuals` uses real PostgreSQL and recorded model outputs. It needs the current
schema but no API credentials, S3, or worker. A missing database or stale recording fails the
eval instead of skipping. Rows are isolated and rolled back. `--live` makes paid provider calls
using only checked-in source-backed/synthetic fixture text; `--report PATH` records outcomes.
Read [manual evaluations](manual-evaluations.md#running-and-updating) before replacing recordings.
The suite does not yet evaluate generated answers or visual interpretation.
