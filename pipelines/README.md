# Pipelines

Multi-step jobs. Celery must call `process(...)` here instead of embedding the work in a task.

| Pipeline | Used by |
| --- | --- |
| `health.py` | `workers.tasks.health` (worker liveness example) |

`attachment_processing.py` claims and commits work through the shared domain service,
calls the scanner adapter, and commits a fenced outcome. The current scanner reports
not_scanned; it does not read or inspect file contents. Document ingestion is described below; garage generation remains future work.

`document_pipeline.py` reads a hash-verified PDF snapshot, extracts/classifies native pages,
and commits each result through DocumentIngestionService. Retry retains completed matching
pages; OCR/vision routes remain pending until provider integration. See the
[4.2 handoff](../docs/implementation-progress.md#page-ingestion-42--2026-09-11).

`document_index.py` builds section/chunk plans from a verified PDF and completed saved pages,
then embeds batches through the shared port. DocumentIndexService fences stale attempts and
reuses matching prior embeddings. See [4.3 details](../docs/document-indexing.md).
