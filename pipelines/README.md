# Pipelines

Document ingestion, garage generation, and other multi-step jobs live here.

Celery tasks in `workers/` should stay thin: `task → pipeline.process(...)`.
