# Vroometr

Web-first motorcycle and dirt-bike ownership platform. Tagline: **Know your machine.**

Durable bike facts live in Postgres, not in AI memory. The website look comes from a visual mock; the code in this repo is a clean rewrite.

## Where things live

| If you want to change… | Open |
| --- | --- |
| Product / architecture decisions | local `docs/design/` (not in git) |
| Website UI | `apps/web/` |
| API rules and endpoints | `services/api/` (not built yet — task 0.3) |
| Background jobs | `workers/` + `pipelines/` |
| Shared Python helpers | `libs/` |
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
infra             Docker Compose: Postgres, Redis, LocalStack
deploy            Production deploy config
evals             AI / RAG evals
tests             Unit and integration tests
docs/adr          Architecture decision records
```

## How to run (right now)

API and garage UI are not here yet. You can run the website starter and the local data stores.

### Local data stores (Postgres, Redis, S3)

Requires Docker.

```bash
./scripts/dev-up.sh
```

Ports and passwords live in `.env` (see [`.env.example`](.env.example)). Details in [`infra/README.md`](infra/README.md).

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
