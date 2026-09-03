# Vroometr

Web-first motorcycle and dirt-bike ownership platform. Tagline: **Know your machine.**

Durable bike facts live in Postgres, not in AI memory. The website look comes from a visual mock; the code in this repo is a clean rewrite.

## Where things live

| If you want to change… | Open |
| --- | --- |
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

Garage HUD is a static visual shell over the default scene. Copy is placeholder until bikes are real.

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

See [`services/api/README.md`](services/api/README.md).

### Worker

```bash
source .venv/bin/activate
./scripts/worker-dev.sh
```

See [`workers/README.md`](workers/README.md).

### Website

```bash
cd apps/web
npm install
npm run dev
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

## Design

V1 product decisions live in local `docs/design/` and are not committed to this repo. Decisions marked **LOCKED** stay the source of truth while implementing.
