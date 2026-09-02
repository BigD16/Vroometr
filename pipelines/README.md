# Pipelines

Multi-step jobs. Celery must call `process(...)` here instead of embedding the work in a task.

| Pipeline | Used by |
| --- | --- |
| `health.py` | `workers.tasks.health` (worker liveness example) |

Document ingestion and garage generation will land here later.
