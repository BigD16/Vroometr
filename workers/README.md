# Workers

Celery tasks are thin wrappers: `task → pipeline.process(...)`.

Do not put ingestion, garage generation, or other job logic in this folder.

## Run

Compose (Redis) should already be up:

```bash
source .venv/bin/activate
./scripts/worker-dev.sh
```

Broker/backend: `REDIS_URL`. Log level: `CELERY_LOG_LEVEL`.

## If you want to change…

| Change | File |
| --- | --- |
| Redis URL / log level | `.env` |
| Celery app (broker) | `workers/celery_app.py` |
| A new job | add `pipelines/<job>.py` with `process()`, then a one-line task in `workers/tasks.py` |
