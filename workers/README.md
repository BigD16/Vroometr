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

Attachment checks use `workers.tasks.process_attachment` →
`pipelines.attachment_processing.process`. Postgres stores status; Redis transports job IDs.
Set `PROCESSING_LEASE_SECONDS` in `.env` and apply migration `0009_attachment_processing`.
Restart the worker after adding this task. The current scanner is explicitly unconfigured.

`vroometr.process_document` delegates to `pipelines.document_pipeline.process`. Apply migration
`0011_document_ingestion` and restart the worker to register this task. It reuses
`PROCESSING_LEASE_SECONDS`; no new environment keys or dependencies.

`vroometr.index_document` delegates to `pipelines.document_index.process` for 4.3. Apply
`0012_document_chunks`, install updated dependencies, configure embeddings, and restart the
worker. Without credentials, sections/chunks save and embedding work awaits configuration.
