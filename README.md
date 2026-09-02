# Vroometr

Web-first motorcycle and dirt-bike ownership platform. Tagline: **Know your machine.**

Durable bike facts live in Postgres, not in AI memory. The website look comes from a visual mock; the code in this repo is a clean rewrite.

## Where things live

| If you want to change… | Open |
| --- | --- |
| Product / architecture decisions | local `docs/design/` (not in git) |
| Website UI | `apps/web/` |
| API rules and endpoints | `services/api/` |
| Background jobs | `workers/` + `pipelines/` |
| Feature flags / AI ports | `libs/vroometr/flags.py`, `libs/vroometr/ai/` |
| AI quality checks | `evals/` |
| Schema change records | `docs/adr/` |
| Local Postgres / Redis / S3 | `.env` (values) and `infra/` (Compose) |

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

Garage UI is not here yet. You can run local data stores, the API, the worker, and the website starter.

### Local data stores (Postgres, Redis, S3)

Requires Docker.

```bash
./scripts/dev-up.sh
```

Ports and passwords live in `.env` (see [`.env.example`](.env.example)). Details in [`infra/README.md`](infra/README.md).

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

See [`services/api/README.md`](services/api/README.md).

### Worker

```bash
source .venv/bin/activate
./scripts/worker-dev.sh
```

See [`workers/README.md`](workers/README.md).

### Website (starter page)

```bash
cd apps/web
npm install
npm run dev
```

Then open http://localhost:3000

### Python tests and lint

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

## Design

V1 product decisions live in local `docs/design/` and are not committed to this repo. Decisions marked **LOCKED** stay the source of truth while implementing.
