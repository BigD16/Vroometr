# Vroometr

Web-first motorcycle and dirt-bike ownership platform. Tagline: **Know your machine.**

Durable bike facts live in Postgres, not in AI memory. The website look comes from a visual mock; the code in this repo is a clean rewrite.

## New developer start here

Read the [documentation index](docs/README.md), [V1 roadmap](docs/roadmap.md),
[implementation guide](docs/developer-guide.md), and [development runbook](docs/development-runbook.md).
They cover the planned sequence, the implemented system through task 4.5 first retrieval evals, setup, data flows,
known gaps, and verification. The [documentation standard](docs/documentation-standard.md)
applies after every task.

## Where things live

| If you want to change… | Open |
| --- | --- |
| V1 phase/task sequence | `docs/roadmap.md` |
| Product / architecture decisions | local `docs/design/` (not in git) |
| Website UI | `apps/web/` |
| Default garage / rides scenes | `apps/web/public/default-garage.jpg`, `rides-track.jpg` |
| API rules and endpoints | `services/api/` |
| Background jobs | `workers/` + `pipelines/` |
| Feature flags / AI ports | `libs/vroometr/flags.py`, `libs/vroometr/ai/` |
| AI quality checks | `evals/` |
| Schema change records | `docs/adr/` |
| Local Postgres / Redis / S3 | `.env` (values) and `infra/` (Compose) |
| CI (lint, tests, image build) | `.github/workflows/ci.yml` |

Layout:

```text
apps/web          Next.js UI
services/api      FastAPI backend
libs              Shared Python
pipelines         Multi-step processing
workers           Celery tasks (thin wrappers)
infra             Docker Compose: Postgres, Redis, LocalStack, Unleash
deploy            Production deploy config
evals             AI / RAG evals
tests             Unit and integration tests
docs/adr          Architecture decision records
```

## How to run (right now)

Garage HUD, Garage pages, and the dashboard use real owner-scoped combustion or electric bikes. The dashboard shows live machine identity, powertrain, and engine hours; maintenance and ride cards stay honest empty states until those records exist. Documents supports authenticated browser-direct uploads, bike-scoped file lists, private view/download, and unlink/delete controls with pooled storage quota.

### Local data stores (Postgres, Redis, S3)

Requires Docker and a filled-in `.env` (copy `.env.example` and set every value).

```bash
./scripts/dev-up.sh
```

Copy [`.env.example`](.env.example) to `.env` and fill in every value. Details in [`infra/README.md`](infra/README.md).

### API

```bash
source .venv/bin/activate
cd services/api
alembic upgrade head
cd ../..
./scripts/api-dev.sh
```

- http://localhost:8000/health/live
- http://localhost:8000/health/ready
- http://localhost:8000/health/deps
- http://localhost:8000/v1/bikes (Clerk JWT; current user's machines)
- http://localhost:8000/v1/uploads/presign (Clerk JWT; private direct-upload grant)

See [`services/api/README.md`](services/api/README.md).

### Worker

```bash
source .venv/bin/activate
./scripts/worker-dev.sh
```

See [`workers/README.md`](workers/README.md).

### Website

```bash
cd apps/web && npm install && cd ../..
./scripts/web-dev.sh
```

Then open http://localhost:3000 — signed-out visits redirect to `/sign-in`; the garage HUD requires a Clerk session. See [`apps/web/README.md`](apps/web/README.md).

### Python tests and lint

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

### GitHub Actions

Every push to `main` and every pull request runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml): Python lint/tests, Next.js lint/build, and Docker image builds. Open the **Actions** tab on GitHub to see a run.

## Implementation progress

Phase 3 now includes uploads, Documents management, pooled quota, and persistent processing status. The scanner hook explicitly reports not scanned until a real scanner is configured. See [progress and review notes](docs/implementation-progress.md) for the walkthrough and review. Phase 4.1 adds PDF document records, confirmed metadata, edition history, primary manual selection, and duplicate warnings; 4.2 adds asynchronous native-text extraction, page routing, partial retries, and review controls. 4.3 adds section hierarchy, source-linked chunks, pgvector embeddings, and review controls. 4.4 adds hybrid document search with reranking, source citations, and private PDF links; see the [retrieval handoff](docs/document-retrieval.md). OCR/vision providers remain deferred; 4.5 adds [source-backed retrieval evals](docs/manual-evaluations.md); 5.1 is next. Live search requires embedding and reranker configuration.

## Design

V1 product decisions live in local `docs/design/` and are not committed to this repo. Decisions marked **LOCKED** stay the source of truth while implementing.
