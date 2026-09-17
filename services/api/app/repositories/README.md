# Repositories — SQLAlchemy queries live here, not in routes or Celery tasks.

`users.py` loads and saves the `users` row, including its persistent active-bike reference. Role and entitlement stay in this database; Clerk is only an identity proof.

`parental_consents.py` stores versioned guardian approvals for 13–17 users.

`bikes.py` loads and saves owner-scoped machines. `get` and `list_for_user` always filter by `user_id` so another rider's bike is never returned.

`attachments.py` loads and saves upload metadata. Every lookup includes both attachment id and
owner id so unknown and foreign attachments have the same not-found behavior.

`attachment_links.py` stores generic relationships. Reads join attachments to filter by owner;
creation deduplicates the same relationship atomically. Target ownership is also checked by
the domain service. Attachment deletion cascades link rows; unlinking never deletes a file.

`attachments.py` also totals quota by file, lists account files, locks the owning user row for
mutations, and deletes attachment metadata after successful storage cleanup. Link rows cascade
with the attachment; removing an individual link never changes quota.

`attachment_processing.py` keeps one current processing attempt per attachment. Queries join
attachments for ownership and refresh state after locking to avoid stale worker claims.
Queued messages are collected for publication after the request transaction commits.

`documents.py` persists document records and provides owner-scoped list/hash queries and
primary updates. Version and confirmation decisions remain in DocumentService.

`document_ingestion.py` persists job/page rows and collects messages for dispatch after commit.
These internal operations require the calling DocumentIngestionService to authorize the document.

`document_index.py` stores indexing jobs, section hierarchy, source chunks, and pgvector
embeddings. Atomic plan replacement is separate from per-batch embedding commits. The
DocumentIndexService authorizes these internal operations.

`retrieval.py` owns hybrid-search SQL: exact pgvector cosine search, GIN-backed PostgreSQL
keyword search, same-section adjacent chunks, and final source-snapshot validation. All share
`_eligible` ownership/source-state/version predicates. See [4.4](../../../../docs/document-retrieval.md).

`conversations.py` loads and saves owner-scoped threads, messages, and context boundaries.
Conversation lookups always include `user_id`. Bike-filtered lists match either
`initial_bike_id` or `current_bike_id`.
