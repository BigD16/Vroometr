# FastAPI backend

Start with the [implementation guide](../../docs/developer-guide.md) for cross-service flows
and the [runbook](../../docs/development-runbook.md) for setup and troubleshooting.

```text
routes/        HTTP only (validate, identify, call a service, return JSON)
services/      business rules (users, age gate, bikes, uploads)
repositories/  database access (users, parental_consents, bikes, attachments)
auth/          Clerk JWT + webhook signature checks
storage/       AWS S3 adapter behind the upload service port
```

Migrations are explicit (`alembic upgrade head`). The app does **not** migrate on startup.

## Run

From the repo root, with Compose already up:

```bash
source .venv/bin/activate
cd services/api
alembic upgrade head
cd ../..
./scripts/api-dev.sh
```

- Liveness: http://localhost:8000/health/live
- Readiness: http://localhost:8000/health/ready (needs Postgres)
- Dependencies: http://localhost:8000/health/deps (Postgres, Redis, LocalStack)
- Current user (Clerk session): http://localhost:8000/v1/me
- Active bike: `GET/PUT /v1/me/active-bike`
- Age eligibility: `GET /v1/me/eligibility`, `POST /v1/me/date-of-birth`, `POST /v1/parental-consents`
- Bikes (signed-in owner only; combustion or electric): `GET/POST /v1/bikes`, `GET/PATCH /v1/bikes/{id}`
- Uploads (signed-in owner only): `POST /v1/uploads/presign`, `POST /v1/uploads/{id}/complete`
- Attachment links (signed-in owner only): `POST/GET /v1/attachment-links`, `DELETE /v1/attachment-links/{id}`; current target type: `bike`
- Files: `GET /v1/attachments`, `GET /v1/attachments/{id}/access`, `DELETE /v1/attachments/{id}` with `confirmed: true`
- Processing: `POST /v1/attachments/{id}/processing` (run/retry); file lists include persistent processing and scan status
- Account storage usage: `GET /v1/storage` (pending uploads reserve quota)
- Clerk webhook: `POST /v1/webhooks/clerk`

## If you want to change…

| Change | File |
| --- | --- |
| Ports / DB password | repo-root `.env` |
| How env is read | `libs/vroometr/settings.py` (values in `.env`) |
| Health checks | `app/health_checks.py` and `app/routes/health.py` |
| Error JSON shape | `app/errors.py` |
| Tables | new SQLAlchemy models + a new Alembic revision (`app/models/`) |
| Users / roles / entitlements | `app/models/user.py`, `app/services/users.py` |
| Clerk session / `/v1/me` | `app/auth/tokens.py`, `app/deps.py`, `app/routes/me.py` |
| Clerk webhook | `app/auth/webhooks.py`, `app/routes/clerk_webhooks.py` |
| Age gate / parental consent | `app/services/age_gate.py`, `app/routes/age_gate.py` |
| Bikes / garage machine rows | `app/models/bike.py`, `app/services/bikes.py`, `app/routes/bikes.py` |
| Persistent active bike | `app/services/active_bikes.py`, `app/routes/active_bike.py` |
| Direct private uploads | `app/services/uploads.py`, `app/storage/s3.py`, `app/routes/uploads.py` |
| Link/reuse uploaded files | `app/services/attachment_links.py`, `app/routes/attachment_links.py` |
| File access / deletion / pooled quota | `app/services/attachments.py`, `app/services/storage_quota.py` |
| Attachment processing / retry / scan hook | `app/services/attachment_processing.py`, `app/processing/`, `app/scanning/ports.py` |
| A new HTTP endpoint | `app/routes/` (keep logic out of the route) |

Processing requires migration `0009_attachment_processing`, `PROCESSING_LEASE_SECONDS` in `.env`,
and a restarted Celery worker. The placeholder scanner never reports clean.

Document records (4.1) use migration `0010_documents` and the PyMuPDF dependency.
`GET/POST /v1/documents`, `POST /v1/documents/{id}/confirm`, and
`PUT /v1/documents/{id}/primary` call `DocumentService` for owner authorization, PDF preflight,
metadata confirmation, duplicate warnings, and edition/primary rules. Originals are referenced
through attachments. Native-text extraction/routing is available in 4.2; see the root implementation progress notes.

Document ingestion (approved 4.2 scope) adds `GET/POST /v1/documents/{id}/ingestion`.
Apply `0011_document_ingestion` and restart API/worker. Confirm a document, then explicitly
queue extraction. Native text and per-page routing/provenance persist; incomplete-page retry
preserves completed results. OCR/vision providers remain unconfigured. See the
[4.2 handoff](../../docs/implementation-progress.md#page-ingestion-42--2026-09-11).

Section/chunk indexing (4.3): `GET/POST /v1/documents/{id}/index`, migration
`0012_document_chunks`, pgvector Python adapter, and server-side embedding configuration.
GET supports chunk `offset`/`limit`; POST queues a background build/retry. See the
[indexing handoff](../../docs/document-indexing.md) for provenance, reuse, staleness, and setup.

Hybrid search (4.4): `POST /v1/retrieval` accepts `bike_id`, `query`, and optional strict boolean
`include_reference_editions`. The route calls `RetrievalService` → `RetrievalRepository` with
shared ownership/freshness filtering, then the model ports for embeddings/reranking. Responses
contain exact source excerpts, citations, partial flags, match strength, and diagnostics. Apply
`0013_retrieval_fts`, configure `RERANKER_MODEL` and `RERANKER_TIMEOUT_SECONDS` with the existing
OpenAI/embedding settings, and restart API. Search adds no worker. See the
[retrieval handoff](../../docs/document-retrieval.md).

The [4.5 manual eval suite](../../docs/manual-evaluations.md) exercises the existing retrieval
service/repository with isolated, rolled-back PostgreSQL fixtures. It adds no API contract or
runtime behavior. Default replay makes no provider calls; explicit live mode measures current
embedding/reranker outputs against the same source-backed gold cases.
