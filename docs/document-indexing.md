# Document sections, chunks, and embeddings (4.3)

Implemented 2026-09-11. This prepares sources for retrieval in 4.4; it does not answer
mechanical questions or implement OCR/vision. Start with the [developer guide](developer-guide.md)
and [runbook](development-runbook.md) for the rest of the system.

## Configuration

Apply migration `0012_document_chunks` and install the updated Python dependencies:
`pgvector` is newly required for SQLAlchemy vector columns. The local migration is applied
and pgvector Python 0.5.0 is installed. Postgres uses its existing vector extension; no new
service or database was introduced. The HTTP adapter uses the existing HTTPX dependency.

Configure these server-side keys in the root `.env`:

| Key | Meaning |
| --- | --- |
| `OPENAI_API_KEY` | Your OpenAI API credential; enter it locally, never in chat, Git, or browser code |
| `OPENAI_BASE_URL` | API base URL including its version path, from official provider configuration |
| `EMBEDDING_MODEL` | Locked working choice is `text-embedding-3-small`; the schema stores 1,536 dimensions |
| `EMBEDDING_VERSION` | Explicit local configuration revision; bump when embedding behavior changes |
| `EMBEDDING_TIMEOUT_SECONDS` | Positive HTTP timeout for an embedding request |
| `PROCESSING_LEASE_SECONDS` | Existing stalled-job retry lease, also used for indexing |

Local embedding settings and the API key are configured, and a live synthetic-text smoke
check passed on 2026-09-11. Other environments must fill their own settings. `.env.example` contains key names only;
CI provides the timeout and does not require live provider credentials. Restart API and worker
with their launchers after configuration changes. Keep request timeout comfortably below the
processing lease. A lease is a retry mechanism, not a hard task deadline.

An empty key/base/model/version leaves the embedding factory unconfigured. Sections and chunks
still save, with `awaiting_configuration` status. Once configured, Build sections & embeddings
sends completed-page text to the provider. No original PDF bytes, user identity, or storage
keys are included in the embedding input. Other AI model ports remain unconfigured.

The adapter checks response model identity, batch indexes/count, dimensions, finite numeric
values, and nonzero vectors. It requests float vectors explicitly. Errors expose generic
messages, not provider payloads or credentials. `EMBEDDING_VERSION` is our configuration
revision, not a claim that the provider returned an immutable model snapshot. Operator changes
to model behavior must bump it.

## Architecture and reading order

1. [DocumentIndex.tsx](../apps/web/components/DocumentIndex.tsx): build/retry, polling, hierarchy,
   chunk pagination, source offsets, and configuration/staleness/error labels.
2. [Routes](../services/api/app/routes/document_index.py): `GET/POST /v1/documents/{id}/index`.
   GET returns state, staleness, section hierarchy, counts, and chunks. Query `offset` starts
   at zero; `limit` defaults to 20 and is capped at 100. Vectors and source storage keys are not
   returned. POST queues a document-specific attempt and returns 202; busy attempts return 409.
3. [DocumentIndexService](../services/api/app/services/document_index.py): ownership, extraction
   prerequisites, lease/attempt fencing, provenance validation, reuse, and batch completion.
4. [Repository](../services/api/app/repositories/document_index.py) and
   [models](../services/api/app/models/document_index.py): sections, chunks, vector persistence,
   and job records. Internal repository methods rely on service authorization.
5. [Dispatch](../services/api/app/documents/index_dispatch.py) and
   [pipeline](../pipelines/document_index.py): publish after API commit, claim, hash-check PDF,
   build a plan, save it atomically, then embed/commit batches independently.
6. [Chunk builder](../services/api/app/documents/chunking.py): deterministic hierarchy and
   source spans. [Embedding adapter](../libs/vroometr/ai/embeddings.py) implements the existing
   `EmbeddingModel` port; its factory selects it only when configured.

Celery's `vroometr.index_document` task delegates to the pipeline. The normal route → service →
repository boundary remains intact. Heavy PDF work and external HTTP calls happen outside
transactions. The service locks the owning account during mutations, like the existing file
and ingestion services.

## Hierarchy, boundaries, and provenance

The builder reads the outline from the same hash-verified PDF as the saved extraction. PDF
bookmark levels define parent relationships. A unique case-insensitive title match in extracted
page text supplies an offset; otherwise a single bookmark destination uses a page boundary.
Conflicting or unresolved multiple destinations on one page use explicit page-grouping chunks.
The outline nodes remain recorded so uncertainty is visible rather than silently dropping them.

When no usable outline exists, numbered headings are a labeled heuristic. Unclassified text
gets a Page N section. Section page ranges cover assigned text and descendant chunks; they
are not a guarantee of the printed manual's complete section extent. These fallbacks are not
semantic or vision-based heading recognition and require review on representative manuals.

Chunks respect section and physical-page boundaries. They contain at most 1,200 Unicode
characters, prefer nearby whitespace breaks, and have no overlap. Only leading/trailing
whitespace is removed; interior source text is retained. `cleaned_text` therefore matches the
saved page substring exactly. Global `chunk_index` and per-section `section_chunk_index` start
at zero. `source_span` has zero-based page index, start character, end-exclusive character,
and extraction version; offsets refer to saved native text, not raw PDF bytes or screen pixels.
The UI displays physical page index + 1, not printed page labels.

Every chunk also stores document/section IDs, source SHA-256, content hash, chunking version,
and embedding model/version. Table/diagram words tag `table_candidate`/`diagram_candidate`;
these are not verified table cells, diagram interpretation, or mechanical specifications.
Only completed page text is indexed. Failed and provider-pending OCR/vision pages stay excluded.
Text is untrusted source data and is rendered as escaped text; it grants no tool permissions.

## Retries, stale work, and failures

Indexing requires confirmed ownership and completed/partial extraction. Known infected files
are blocked on queue, status, claim, and result writes. Each attempt captures its source
extraction attempt. Starting extraction again makes old indexing results stale and fences late
writes. Changing embedding model/version or chunking version also labels the index stale.
Future retrieval must filter stale indexes, enforce ownership/infection rules, and use a matching
query embedding configuration; merely finding a stored vector is insufficient.

The section/chunk replacement is transactional. Embeddings then commit in batches of at most
16. A retry reuses this document's exact content hashes under the same model/version and only
embeds missing inputs. Other documents are untouched. Existing successful batches survive
provider failure. Model/version changes re-embed the selected document. Deleted sources cannot
be recreated by late workers.

Broker errors are recorded when possible. A crash between commit and publish leaves a queued
attempt for manual retry after the lease. Native extraction being partial produces a partial
index even when every eligible chunk is embedded. Empty/blank-only sources produce no chunks
and are partial. Automatic reconciliation and scheduled reindexing are not implemented.

The API paginates returned chunks, but current repository operations still load all chunks for
counts/reuse/status. Large-document query optimization and vector search indexes belong to
subsequent work. No retrieval endpoint exists yet.

## Verification and manual review

217 Python tests passed, including real Postgres vector persistence and pipeline transactions.
Five existing PyMuPDF/SWIG deprecation warnings remain. Provider requests were tested with
HTTPX mock transport and controlled embedding adapters. After Drake configured his key, a
separate live request through the application factory/adapter returned one valid 1,536-dimensional
vector for synthetic sample text on 2026-09-11. No uploaded document was sent. Tests continue
to isolate the embedding factory from developer credentials.

`PYTHONPATH=libs:services/api python -m evals.chunking` passed five offline source-integrity
scenarios and is now included in CI. It checks hierarchy/boundaries, labeled fallbacks,
ambiguous outlines, Unicode/text coverage, incomplete-page exclusion, and candidate tags.
It is not a retrieval relevance or mechanical-answer safety benchmark; those follow in 4.4/4.5.

Ruff, ESLint, TypeScript, and the production webpack build passed. An isolated Chrome harness
using the real component and mock APIs passed hierarchy/text review, pagination, missing-key
status, retry to embedded status, stale-source labeling, and clearing text after access failure.
That temporary harness is not a checked-in live Clerk/browser/provider test suite.

For manual review: restart API/worker, confirm a PDF, extract pages, then choose Build sections &
embeddings. Review a parent/child section and compare a chunk to its source page. Without the
API key, verify sections persist with the configuration message. After configuring the provider,
retry and check embedding counts. Re-extract and confirm the old index is labeled out of date.
The direct provider smoke check has passed. A full browser → worker → live provider → stored
vector review remains a separate manual check after restarting the running processes.

References: [OpenAI embedding API](https://developers.openai.com/api/reference/python/resources/embeddings/methods/create),
[pgvector Python integration](https://github.com/pgvector/pgvector-python), and
[PyMuPDF document outlines](https://pymupdf.readthedocs.io/en/latest/document.html).
