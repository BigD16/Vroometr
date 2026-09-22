# Implementation progress

Last reviewed: 2026-09-22. The repository [V1 roadmap](roadmap.md) owns the numbered sequence
and phase status. This file records verification evidence and handoffs. The expanded 3.3
scope below was approved by Drake and supplements the original roadmap.

- Foundation, auth/shell, and bike/garage/dashboard work are present through Phase 2.
- **3.1 complete:** private browser-direct uploads with owner-scoped attachment metadata
  and server verification before marking an upload complete.
- **3.2 implemented (backend):** generic attachment relationships, create/list/unlink API,
  ownership checks, retry-safe insertion, and database/unit/API tests.
- **3.3 implemented:** pooled account storage quota and Documents management UI, including
  private view/download access, upload-and-link, unlink/relink, and confirmed file deletion.
- **3.4 implemented:** durable processing attempts, Celery pipeline, explicit unconfigured
  scanner, and Documents status/retry controls.
- **3.4 follow-up planned:** [real malware scanning](#planned-follow-up-real-malware-scanning)
  remains unimplemented; tracked separately from the completed processing framework.
- **4.1 implemented:** PDF document records, explicit metadata confirmation, version groups,
  primary manual selection, and duplicate warnings.
- **4.2 implemented (approved scope):** async native-text extraction, visual routing, page
  provenance, partial failure/retry, and review UI. OCR/vision providers remain deferred.
- **4.3 implemented:** sections, exact chunk provenance, pgvector embeddings via the model
  port, durable retry/reuse, and review UI. Live synthetic-text provider verification passed.
- **4.4 implemented:** authorized hybrid retrieval, scored reranking, bounded cited passages,
  and document search UI. Offline/live synthetic evals passed.
- **4.5 first evals implemented:** twelve source-backed/synthetic retrieval cases, recorded/live
  providers, exact provenance and abstention gates, CI replay, and a saved live report.
- **5.1 implemented:** bike-scoped conversations, messages, deterministic rolling summaries,
  explicit bike-switch context boundaries, owner-scoped HTTP API, Next proxies, and a minimal
  Assistant UI that stores user messages only (no ReasoningAgent / replies yet).
- **5.2 implemented:** always-load `CompactContextPack` (bike identity/hours/powertrain, recent
  turns, rolling summary, deferred mods/maintenance/ride stubs), context budget, conversation
  context endpoint, and Assistant panel. On-demand manuals remain `RetrievalService.search`.
- **5.3 implemented:** read-only assistant tool registry wrapping the same domain services as
  HTTP (`get_bike`, `get_compact_context`, `search_manuals`, `get_conversation`). Mutating tools
  and the ReasoningAgent loop remain deferred.
- **5.4 implemented:** write-policy gate (`auto` vs `confirm`, `FLAG_AI_WRITES`, confirmation /
  explicit-instruction on `ToolContext`). Default registry still has no durable write tools.
- **5.5 implemented:** citation/safety helpers (`evaluate_claim_answer`, `decide_from_retrieval`,
  escalation reasons). Withholds unverified safety-critical exact values; escalates sparingly.
- **5.6 implemented:** hierarchical conversation memory — search bike-scoped rolling summaries,
  then expand bounded raw-message spans (`HierarchicalMemoryService` + memory tools). Lexical
  ranking until summary embeddings are wired.
- **5.7 implemented:** Assistant UI polish — role-styled messages, composer affordances,
  expandable `AssistantSources` chips (5.5 citation shape), shell FAB a11y, page disclaimer.
  Agent replies still deferred. **Phase 6 / ReasoningAgent is next.**
- **Developer documentation established:** repository onboarding guide, setup/troubleshooting
  runbook, and required documentation updates after every task. Start at [docs index](README.md).

## Planned follow-up: real malware scanning

Added to the repository [roadmap](roadmap.md) at Drake's request on 2026-09-10. Status:
**not started**. This is a follow-up to 3.4; it does not renumber phases or change 4.2 as the
next scheduled task at the time of addition. Implementation scheduling and scanner selection remain open.

Scope and completion criteria:

- [ ] Select a real scanner and implement the existing `MalwareScanner` port. Document its
  deployment, resource needs, signature updates, and configuration. Obtain explicit approval
  before introducing new infrastructure; this backlog entry does not select a product.
- [ ] Scan the actual private file bytes through the existing Celery/pipeline/domain-service
  path, preserving backend ownership checks and durable attempt state.
- [ ] Bind each verdict to the exact immutable object/version being served. A replacement
  upload must not inherit an earlier clean verdict. Coordinate this with 4.2 ingestion.
- [ ] Persist clean/infected results and scanner provenance. Handle unavailable scanners,
  timeouts, and failures explicitly; never report these as clean or clear a prior infected verdict.
- [ ] Preserve infected-file blocking for new view/download grants and enforce it in document
  ingestion. Document the access policy for pending/unscanned files and existing read grants.
- [ ] Support run/retry for existing unscanned files using the existing attempt/lease controls.
  Show accurate scanning, clean, infected, and failed states in Documents.
- [ ] Add real-scanner integration coverage using a benign file and a standard harmless
  antivirus test fixture, plus timeout/unavailability, changed-object, retry, stale-attempt,
  and owner-isolation tests. Record which checks run locally and in CI.
- [ ] Update setup, operations, configuration key names, manual review steps, and developer
  documentation before marking scanning complete.

Planning verification: documentation-only change; `git diff --check` passed. No application
tests were rerun, and no scanner, dependency, migration, or infrastructure was added. The
developer guide links this task; runtime setup remains unchanged.

## Upload limits and Documents management (3.3)

- Enforce the 5 GB pooled Pro account quota, preserving PDF/image size limits and the
  exclusions for generated scenes and temporary troubleshooting photos. Count each file
  once regardless of how many records link to it.
- Link completed uploads to the selected bike and show its persistent document list,
  with loading, empty, success, and recoverable error states.
- Add View/Download controls backed by owner-authorized, short-lived private-storage access.
  Uploaded files remain untrusted; viewing must not imply malware scanning has completed.
- Add **Remove from this bike** to delete only that relationship, preserving the file
  and its other links.
- Add a separate **Delete file** action with explicit confirmation that explains its
  effect on every linked record. Delete the stored object and attachment metadata with
  retry-safe failure handling, clean up all links, and reconcile quota usage.
- Verify ownership in backend domain services for all operations. Test cross-account
  denial, file reuse, quota accounting, unlink preservation, and deletion failures.

The Documents page now implements this scope. Its default list follows the active bike;
**Show all account files** exposes unlinked files and pending uploads. **Add to this bike**
reuses an existing uploaded file. A failed verification or link can be retried without uploading
another copy. Preview uses a sandboxed iframe; browsers that cannot preview a file can download it.

Quota includes pending reservations and counts attachment rows, not links. `StorageQuotaService`
locks the account's user row before checking usage and holds that lock until the pending upload
commits. Completion, link changes, and file deletion share that lock. The 5 GB product limit
currently applies to all existing access, including tester/internal accounts; billing/demo
entitlement gates remain Phase 8. Clients cannot select an excluded upload purpose.

Deletion requires explicit confirmation and waits until the 15-minute upload grant expires.
The UI shows the earliest deletion time. Unlinking is immediate. Pending uploads continue to
reserve quota until deleted; there is no automatic abandoned-upload cleanup yet. S3 deletion
happens before metadata deletion: storage failures preserve metadata and quota; if database
cleanup fails after the object is removed, repeating deletion safely completes cleanup.
Foreign and unknown IDs return the same 404. Private access grants last 60 seconds and are
issued only for owned, uploaded attachments, with no-store responses.

No new migration, environment variable, dependency, or infrastructure is needed for 3.3.
Migration `0008_attachment_links` from 3.2 must be applied. Malware scanning and document
processing remain later tasks; uploaded status means metadata verification, not a malware verdict.

### 3.3 developer review

Read in order:

1. `apps/web/components/DocumentLibrary.tsx` — list, preview, actions, and confirmation;
   `DocumentUpload.tsx` — browser upload, verification, and link retry.
2. `apps/web/app/api/attachments/` and `services/api/app/routes/attachments.py` — authenticated
   web proxy and FastAPI contract. `lib/fastapi.ts` now correctly forwards empty 204 responses.
3. `services/api/app/services/attachments.py` — file access/deletion rules;
   `storage_quota.py` — pooled quota policy, used by `uploads.py` before signing uploads.
4. `services/api/app/repositories/attachments.py` — account locking and usage queries;
   `app/storage/s3.py` — signed reads and idempotent object deletion.

Additional endpoints: `GET /v1/storage`, `GET /v1/attachments` (optional `bike_id`, `include_all`),
`GET /v1/attachments/{id}/access?download=true|false`, and `DELETE /v1/attachments/{id}` with
`{"confirmed": true}`. Authorization remains in the backend domain services.

Manual review: upload a PDF or image on Documents, preview/download it, remove its bike link,
then find it in account files and reattach it. Select another bike and check the list changes.
After the upload grant expires, confirm permanent deletion and verify the file disappears
from every linked bike and account usage drops. Try Cancel first to verify no deletion occurs.

Verification: **156 Python tests passed**; Ruff, web ESLint, and `git diff --check` passed.
Unit/API/Postgres/LocalStack tests cover quota boundaries and concurrency,
file reuse, authorization, private reads, and deletion failure/retry behavior. A temporary
headless Chrome harness exercised the real React components with mock API responses: list,
sandboxed preview, unlink/relink, confirmation, storage failure/retry, upload-and-link, and
bike switching all passed. This was component-level browser verification, not a live Clerk
session test. Next.js production build and TypeScript passed with `--webpack`; default
Turbopack encountered an environment port-binding restriction. Build configuration is unchanged.

## Attachment links (3.2)

`route → AttachmentLinkService → AttachmentLinkRepository → Postgres`

One attachment can link to several entities and each entity can reference several files.
The relationship is unique by attachment, target type/id, and relationship type. Repeating
creation returns the existing link. Unlinking preserves the file and its other relationships.
Deleting an attachment cascades only its link rows.

The API currently accepts `entity_type: "bike"`. Both the attachment and bike must belong to
the signed-in user; unknown and foreign IDs return the same 404. Only verified uploads can
be linked. The schema supports future domain types, but the service rejects them until their
owner-scoped repositories exist. Add ownership validation in `_require_target` when adding
maintenance, modification, or other targets. Polymorphic target IDs have no SQL foreign key;
future permanent target-deletion workflows must clean up their links in the same transaction.
Bikes currently use archive/restore, which preserves links.

Endpoints:

- `POST /v1/attachment-links` with `attachment_id`, `entity_type`, `entity_id`, and optional
  `relationship_type` (defaults to `reference`).
- `GET /v1/attachment-links?entity_type=bike&entity_id=<bike UUID>`.
- `DELETE /v1/attachment-links/<link UUID>` removes only the relationship.

Read in order:

1. `services/api/app/routes/attachment_links.py` — HTTP contract/error mapping.
2. `services/api/app/services/attachment_links.py` — ownership and upload-state rules.
3. `services/api/app/repositories/attachment_links.py` — owner-filtered reads and atomic deduplication.
4. `services/api/app/models/attachment_link.py` — relationship schema and constraints.
5. `tests/unit/test_attachment_links.py`, `tests/api/test_attachment_links_http.py`, and
   `tests/integration/test_attachment_link_repository.py` — behavior and persistence checks.

Migration: `0008_attachment_links`; additive, no rewrites of existing attachments.
No new environment variables, dependencies, or infrastructure. No frontend changes in this
slice: the Documents upload panel does not yet create or display links. Downloads, document
processing, maintenance targets, and modification targets remain future work.

Manual API review: using a signed-in session, upload and complete a file through the existing
upload flow. Create a link to an owned bike, repeat the request and confirm the same link ID,
then list it. Link that attachment to a second owned bike and remove the first link; the second
link should remain. A different account must receive 404 for either bike or attachment.

## Verification for 3.2

- Full Python suite: **137 passed**, including Postgres and LocalStack integration tests.
- Ruff and `git diff --check`: passed.
- `alembic upgrade head`: applied `0008_attachment_links` to local Postgres.
- `alembic check`: attachment-link schema has no reported differences, but the global check
  fails on pre-existing drift: migration `0003_parental_consents` creates
  `ix_parental_consents_minor_user_id`, which its SQLAlchemy model does not declare.
  It also warns about the existing `users`/`bikes` foreign-key cycle. These are unchanged
  and should be addressed separately before relying on a clean global schema-drift gate.


## Processing state and scan hook (3.4)

Upload completion saves a queued processing attempt in the same Postgres transaction as
upload verification. The API publishes the message only after committing. The worker follows:

`Celery task → attachment_processing.process → AttachmentProcessingService → repository → Postgres`

The pipeline commits a running claim, calls the scanner outside the database transaction,
then commits the outcome. Every message carries the owning user ID, attachment ID, and an
attempt ID. Owner checks and locking apply in the service. Duplicate claims and results from
superseded attempts are ignored. Deleted attachments are not recreated by delayed jobs.

`attachment_processing` has one current attempt per attachment, with processing state
(queued/running/completed/failed), independent scan status (not_scanned/clean/infected/error),
version metadata, error code, timestamps, and retry time. Existing files have no attempt;
the API reports `not_started` and `not_scanned`. No existing file is backfilled as clean.

The only wired scanner is `UnconfiguredScanner`. It returns `not_scanned`; **a completed
processing attempt does not mean a malware scan passed**. Real malware scanning is not
implemented. The port in `app/scanning/ports.py` is the integration point for a future adapter.
Before enabling a real scanner, bind its verdict to the exact immutable object/version being
served, enforce scanner timeouts, and validate the adapter with real scanner tests. No scanner
product, daemon, or new infrastructure was added in this slice.

Documents displays backend status and polls while work is queued/running. Run checks starts
processing for older files. Retry checks restarts failed or completed attempts, or queued/running
attempts after their configured lease. Broker failures are persisted as failed when possible;
a crash between commit and publish leaves a durable queued row that can be manually retried
after its lease. Automatic reconciliation/scheduled recovery is not implemented yet.

Infected files cannot receive new View/Download grants. Errors and the unconfigured scanner
cannot clear a prior infected verdict. Its scanner provenance is retained. Unscanned files
retain the existing access behavior with an explicit label. Previously issued 60-second read
grants cannot be immediately revoked; already downloaded data cannot be recalled.

### Files to read

1. `app/routes/attachment_processing.py` — owner-authenticated retry API and status schema.
2. `app/services/attachment_processing.py` — queue, exclusive claim, retry lease, and fenced finish.
3. `app/repositories/attachment_processing.py` and `app/models/attachment_processing.py` —
   persistence, post-commit message collection, and schema.
4. `app/processing/dispatch.py`, `app/deps.py`, and `pipelines/attachment_processing.py` —
   publication after commit, queue failure handling, and worker transactions.
5. `apps/web/components/ProcessingStatus.tsx` and `DocumentLibrary.tsx` — labels, polling, retry,
   and blocked access controls. Server authorization remains in `app/services/attachments.py`.

Paths starting with `app/` are under `services/api/`.

### Setup and review

- Migration: `0009_attachment_processing` (applied to local Postgres).
- New env key: `PROCESSING_LEASE_SECONDS` — configured locally to 300 seconds; `.env.example`
  lists only its name, and CI supplies a test value. No new dependencies.
- Restart the API and worker to load the new code. `scripts/worker-dev.sh` now includes
  `services/api` on its Python path so the worker can call the shared domain services.
- Endpoint: `POST /v1/attachments/{id}/processing` returns 202 for an accepted attempt.
  Attachment list responses now include `processing`. No client-supplied scan verdict is accepted.
- Upload a file with the worker running. Observe Checks queued/running → Checks finished ·
  Not scanned (the transition may be fast). Refresh and confirm status survives.
- Use Run checks on an older upload. For a stalled queue, wait until the displayed retry time,
  restart the worker, and retry. A failed attempt can be retried immediately.

### Verification

175 Python tests passed, including Postgres/LocalStack integration and a real Celery worker
on an isolated Redis test queue. Coverage includes rollback without publication, committed
state visibility, broker/scanner failures, duplicate/concurrent claims, stale completion,
deletion during scanning, owner isolation, and backend rejection of infected-file access.
Real malware detection is not claimed by these tests; scanner outcomes are test doubles.

Ruff, web ESLint, final TypeScript checking, and `git diff --check` passed. The production
build passed using `npm run build -- --webpack`. The isolated headless Chrome component
harness passed status polling (queued through completed/not_scanned), retry initiation,
preview, unlink/relink, delete confirmation/failure/retry, upload-and-link, and bike switching.
Browser tests used mock API responses; the separate worker test used real Redis and Postgres.


### 3.4 launcher fix

The first manual run exposed an API startup path bug: `scripts/api-dev.sh` changes into
`services/api`, but the publisher imports the root-level `workers` package. The launcher now
exports the same repo/lib/API Python paths as the worker launcher. This requires a full API
restart; Uvicorn code reload cannot change its inherited environment. Existing failed attempts
can then be retried in Documents. Queue-failure logs now include the exception class without
including exception text or secrets.

The regression test executes the launcher from another directory without inherited PYTHONPATH
and invokes the actual publisher with a stubbed broker call. The targeted launcher/processing
suite passed (10 tests); the adjusted CI-compatible launcher test also passed.


## Document records and editions (4.1)

Documents now contains file management and a separate document-record section for the active
bike. Upload a PDF, register it as a manufacturer manual or supporting document, then confirm
its make/model/year. The initial fields come from the bike profile and are explicitly labeled
as defaults, not AI-derived facts. A draft cannot become primary before confirmation.

### Architecture and reading order

The browser calls authenticated Next.js proxies, then FastAPI routes, DocumentService,
repositories, and Postgres. DocumentService uses a PDF inspector backed by private S3 reads.
No AI tools or extraction pipeline were added.

1. `apps/web/components/DocumentRecords.tsx` — registration, confirmation, duplicate warnings,
   edition selection, primary override, and authorized PDF download.
2. `services/api/app/routes/documents.py` — authenticated schemas and HTTP error mapping.
3. `services/api/app/services/documents.py` — DocumentMetadata validation and register,
   confirm, and select_primary business rules.
4. `services/api/app/documents/inspection.py` — PyMuPDF preflight and SHA-256 hashing;
   `services/api/app/storage/s3.py` validates object metadata and bounds the read.
5. `services/api/app/repositories/documents.py`, `services/api/app/models/document.py`, and
   `services/api/alembic/versions/0010_documents.py` — ownership queries and database constraints.

### Rules and failure behavior

- Each record references an existing uploaded attachment; the original file stays in private
  storage. Images remain file attachments in this step.
- Backend ownership checks cover bikes, files, documents, and predecessor editions. Duplicate
  matches are scoped to the account, never another account's documents.
- SHA-256 matches warn without merging or deleting either copy. A version relationship is
  explicitly selected; matching bytes alone do not create one.
- Confirmation of a newer edition archives earlier records in that version group. Confirming
  a manufacturer manual makes it primary; the database permits only one primary per bike.
  A confirmed older manufacturer manual can be selected as primary explicitly.
- Confirmed metadata is preserved. Changes require a new edition. Retrying confirmation
  does not override a later manual primary selection; older unconfirmed drafts cannot replace
  an already-confirmed newer edition.
- Malformed, empty, and encrypted/password-protected PDFs are rejected. Known infected files
  are blocked. Parser acceptance does not certify that a file is safe or malware-free.
- Confirmation and primary selection recheck the stored file hash. Existing upload grants can
  still rewrite bytes until they expire; 4.2 must verify the hash or bind ingestion to an immutable
  snapshot before extracting. This step does not claim immutable storage or implement extraction.
- Removing a generic file link preserves both private storage and document records. Global
  Delete file removes its document records as well as links, with confirmation. Later editions
  retain their version group/revision if their predecessor is deleted.
- Upload/delete actions refresh the document list. Storage outages and validation failures show
  recoverable errors. Registration performs synchronous PDF preflight within the existing size
  limit; extraction/OCR will run asynchronously in 4.2.

### API and setup

- `GET /v1/documents?bike_id=...`
- `POST /v1/documents` registers a draft and returns duplicate IDs/warning.
- `POST /v1/documents/{id}/confirm` confirms metadata.
- `PUT /v1/documents/{id}/primary` selects a confirmed manufacturer manual.

Migration `0010_documents` is applied locally. Install updated Python dependencies in other
workspaces; PyMuPDF is newly required (1.28.2 installed locally), following the locked parser
choice. No new environment variables or infrastructure. Restart the API to load these routes.
Parser reference: [PyMuPDF Document API](https://pymupdf.readthedocs.io/en/latest/document.html).

### Verification and manual review

187 Python tests passed, including real Postgres and LocalStack integration. Coverage includes
owner isolation, confirmation, duplicate warnings, versioning, primary overrides, changed bytes,
encrypted/malformed PDFs, database constraints, and deletion cascades. Five PyMuPDF/SWIG
upstream deprecation warnings remain. Ruff, ESLint, final TypeScript checks, and diff checks
passed. The production webpack build passed; subsequent UI changes passed lint/type checks.

An isolated headless Chrome harness rendered the actual DocumentRecords component with mock
API responses. Registration, corrected confirmation, persistent duplicate warning, edition
archiving, primary override, and encrypted-PDF error display passed. This is not a live Clerk
browser end-to-end test.

For manual review, open Documents for a bike, upload a PDF, register it, correct the metadata,
and confirm. Upload a second copy to see the duplicate warning. Register it as the next edition
and confirm; verify the earlier edition is archived, then choose the earlier manual as primary.
Try a password-protected PDF and confirm the rejection message. Switch bikes to verify scope.

4.2 remains unstarted on the [roadmap](roadmap.md): extraction, page records, OCR/visual
scoring, and AI-proposed document metadata. Before proceeding, explain the
registration-to-confirmation flow, where its rules live, and how you would verify or modify
version/primary behavior.

## Developer onboarding and documentation standard — 2026-09-10

Added a repository handoff covering the current implementation through 4.1, including the
earlier foundation, identity/eligibility, garage, and dashboard work. Another developer can
start without the previous chat or an external Cursor plan.

Reading order:

1. [Documentation index](README.md) — entry point and source-of-truth boundaries.
2. [V1 roadmap](roadmap.md) — numbered phase/task sequence and current status.
3. [Developer guide](developer-guide.md) — capability inventory, architecture, file map,
   domain rules, schema/migrations, security behavior, and explicit unfinished systems.
4. [Runbook](development-runbook.md) — clean-checkout setup, configuration key groups,
   process startup, tests, manual smoke review, and troubleshooting.
5. [Documentation standard](documentation-standard.md) — completion requirements and
   reusable handoff template.

Updated root/API/web/test READMEs to make these guides discoverable. Updated `AGENTS.md`
and Cursor workflow/handoff rules so every task reviews and updates documentation before
completion. Written handoffs stand independently of conversational teach-back.

Reviewed the guidance against source, migrations, tests, scripts, CI, and local design
decisions. Documented material gaps: age/entitlement enforcement, unconfigured scanning/AI,
missing extraction and deployment, temporary browser harness coverage, and Redis/LocalStack
tests absent from current CI services. Private design documents remain ignored by Git;
new developers must obtain them from the project owner.

Verification: checked 41 local Markdown links across nine entry-point/guide files; all
targets exist. `git diff --check` passed. Application tests were not rerun for these prose
and instruction-only edits; prior feature results are explicitly labeled historical.
No application behavior, migrations, dependencies, or environment configuration changed.

Manual review: follow the root README's onboarding links, inspect the capability inventory,
and use the handoff template on the next task. The next product task remains 4.2; this work
does not advance its implementation status.

## Repository V1 roadmap — 2026-09-10

Added [docs/roadmap.md](roadmap.md) as the committed V1 phase/task sequence. Content was
adapted from the previous local Cursor plan, with current status through 4.1, next task 4.2,
approved 3.3 expansion notes, and the malware-scanning follow-up linked from progress.

Updated [docs/README.md](README.md), root README, developer guide, documentation standard,
AGENTS.md, and this progress log so onboarding no longer depends on an external IDE plan.

Verification: documentation-only change; `git diff --check` passed. Application tests were
not rerun. No migrations, dependencies, or environment configuration changed.

Manual review: open `docs/roadmap.md`, confirm the status table matches this progress file,
and follow the docs index reading order.


## Page ingestion (4.2) — 2026-09-11

Implemented the approved scope: native PDF text extraction and routing now, OCR/vision
providers later. Confirmed documents expose Extract pages, persisted status, original-page
text review, and Retry incomplete pages. The roadmap now advances to 4.3; actual malware
scanning and OCR/vision provider benchmarking remain explicit follow-ups.

### Architecture and reading order

1. [DocumentIngestion.tsx](../apps/web/components/DocumentIngestion.tsx) — loading/polling,
   partial results, retry, escaped text excerpts, and recoverable errors.
2. [Ingestion routes](../services/api/app/routes/document_ingestion.py) — owner-authenticated
   `GET/POST /v1/documents/{id}/ingestion`; POST returns 202, busy attempts return 409.
3. [DocumentIngestionService](../services/api/app/services/document_ingestion.py) — confirmation,
   ownership/infection checks, attempt claims, lease renewal, page provenance, and fenced writes.
4. [Repository](../services/api/app/repositories/document_ingestion.py) and
   [models](../services/api/app/models/document_ingestion.py) — jobs/pages and message collection.
5. [Dispatch](../services/api/app/documents/dispatch.py), API `get_db`, and
   [pipeline](../pipelines/document_pipeline.py) — publish after commit, snapshot hash check,
   independent page commits, partial completion, and retry retention.
6. [Extraction](../services/api/app/documents/extraction.py) — PyMuPDF native text and visual
   routing heuristics. The Celery task in `workers/tasks.py` only delegates to the pipeline.

`IngestionMessage` binds owner/document/attempt IDs; `IngestionClaim` contains a value copy of
attachment metadata, expected hash, and completed page indexes. `PIPELINE_VERSION` identifies
this extraction implementation. Each page records original zero-based index, source hash,
text, visual score/reasons, processing class/state, and extraction/OCR/vision versions.

### Rules and limits

- Only an owned, uploaded, confirmed document can be queued. Known infected files cannot be
  queued or read through the page-status API, and infection is rechecked before page writes
  and successful completion. The real malware scanner is still not implemented.
- A worker downloads once and verifies SHA-256 before parsing. All pages use that same bytes
  snapshot. This binds extracted text to the registered hash even if the original key later
  changes; it does not make the original object immutable.
- A page failure saves an explicit failed result while preserving other pages. Retry skips
  completed pages only when hash and extraction version match; late attempts cannot overwrite
  newer results. Deletion does not recreate documents or page records.
- Native pages complete; OCR/enhanced or OCR+vision routes remain pending_provider. Available
  native text is retained. These pages produce a partial job result, not fake OCR output.
  OCR/vision versions remain null. Retrying cannot resolve a missing provider.
- Scoring uses image coverage/count, vector count, sparse text, and visual/instructional hints.
  Thresholds are versioned starting heuristics, not benchmark-validated classification.
  Section context awaits 4.3. Failed classification is explicit even though the stored class
  uses the text_only fallback; its score must not be treated as a successful classification.
- Original PDF page indexes are preserved; displayed page numbers are index + 1, not printed
  page labels. The API/UI show text excerpts up to 4,000 characters; complete native text is
  stored. There are no chunks, embeddings, retrieval, OCR/vision calls, or AI metadata proposals.
- Broker failure is persisted as failed when possible. A crash around publication or a worker
  interruption can leave queued/running state until manual retry after the lease. Page commits
  renew the lease. Automatic recovery and large-document UI pagination remain future work.

The native text/image/vector APIs were checked against the
[official PyMuPDF Page documentation](https://pymupdf.readthedocs.io/en/latest/page.html).

### Setup and verification

Migration `0011_document_ingestion` was applied to local Postgres. No new dependencies,
infrastructure, or environment keys. Reuses `PROCESSING_LEASE_SECONDS`; restart the API and
worker using their launchers so the new routes and Celery task are loaded.

- Full regression run: **197 Python tests passed**, with five existing PyMuPDF/SWIG deprecation
  warnings. Then two additional provenance/image-routing cases were added and the full ingestion
  unit module passed (**7 tests**). No failures remain in those runs.
- New unit/API tests cover owner and confirmation gates, known infection, claim fencing, busy
  leases, stale writes, page provenance, blank/native/visual routing, post-commit publication,
  rollback without publication, and thin worker delegation.
- New real-Postgres pipeline tests cover partial page failure, retention/retry of only incomplete
  pages, stale delivery, changed bytes, deletion, durable broker failure, and infection during
  extraction. These tests use in-memory PDF storage; existing LocalStack tests cover the adapter.
- Ruff, ESLint, TypeScript, and `npm run build -- --webpack` passed. The initial full-suite test
  filename collision was fixed by naming the integration module `test_document_ingestion_db.py`.
- Isolated Chrome component checks passed queued polling, partial results, native text, pending
  provider labels, physical page numbering, error display, and clearing text on access failure.
  These checks used mock APIs and a temporary harness, not a live Clerk/worker browser flow.

Checked-in tests: [unit](../tests/unit/test_document_ingestion.py),
[API](../tests/api/test_document_ingestion_http.py), and
[database/pipeline](../tests/integration/test_document_ingestion_db.py).

### Manual review and documentation

Restart API and worker. In Documents, confirm a PDF's metadata, choose Extract pages, and
expand Review extracted pages. Verify native text and physical page numbering. Try an image
or diagram-heavy PDF; expect Partially extracted and provider-pending pages. Retry incomplete
pages and confirm completed native pages persist. A changed source should show a file-changed
error. Use Refresh extraction after fixing a service outage.

Updated the roadmap, progress summary, developer guide, runbook, documentation index, root/API/
web READMEs, and worker/pipeline/service/repository notes. Review the pipeline and domain service
before modifying retry behavior; use the tests above to verify any change. 4.3 sections/chunks
is next; approved provider deferral does not imply completed OCR or vision capability.


## Sections, chunks, and embeddings (4.3) — 2026-09-11

Implemented section hierarchy, source-preserving chunks, pgvector embeddings through the
existing EmbeddingModel port, durable indexing/retry/reuse, and a paginated review UI.
Read the [4.3 developer handoff](document-indexing.md) for architecture, file reading order,
invariants, failure behavior, configuration, manual review, and limitations.

Migration `0012_document_chunks` is applied locally. Added the pgvector Python adapter
(0.5.0 installed). Existing HTTPX handles provider requests. Added `OPENAI_API_KEY`,
`OPENAI_BASE_URL`, `EMBEDDING_VERSION`, and `EMBEDDING_TIMEOUT_SECONDS`; uses existing
`EMBEDDING_MODEL` and `PROCESSING_LEASE_SECONDS`. Non-secret local settings were populated;
the API key remains blank. Restart API and worker after installation/configuration.
No new infrastructure or locked architecture deviation.

API: `GET/POST /v1/documents/{id}/index`. Building saves sections/chunks even without credentials;
embeddings then report awaiting_configuration. Actual embedding calls require configuration.
Only completed native pages are eligible; OCR/vision provider work and real malware scanning
remain deferred. 4.4 retrieval is next. Do not use stale indexes or mismatched model versions
as retrieval sources.

Verification: 217 Python tests passed, five existing PyMuPDF/SWIG warnings. New coverage includes
real vector round-trips, retry reuse, version changes, provider batch failure, queue failure,
source-attempt invalidation, deletion, ownership, infection, API pagination bounds, and strict
mock HTTP response validation. Five offline chunk/source-integrity eval scenarios passed and
were added to CI. Ruff, ESLint, TypeScript, production webpack build, and isolated Chrome
component checks passed. Browser/provider tests use controlled responses; live OpenAI smoke
verification remains outstanding because credentials are absent.

Updated roadmap status, documentation index, developer guide/runbook, root and affected
subsystem READMEs, and the dedicated indexing handoff. No 4.4 retrieval implementation was added.


### 4.3 live embedding configuration check — 2026-09-11

Drake added the API key locally. A fresh process loaded root `.env`, called the configured
embedding factory/adapter with one synthetic sample string, and validated one returned
1,536-dimensional vector. No key, vector values, or uploaded documents appeared in output.
The restricted-network attempt failed; the approved network-enabled retry passed.

Updated the roadmap, developer guide, and indexing handoff to record the live check. Existing
API/worker processes still require restart to load changed settings. This verifies the live
provider adapter, not the entire browser/worker/storage flow. Application code, dependencies,
and migrations are unchanged; no regression-suite rerun was needed. `git diff --check` passed.
The next numbered task remains 4.4.

## Hybrid document retrieval (4.4) — 2026-09-11

Implemented. Documents now searches the selected bike's primary manual and active supporting
sources; other confirmed editions/archives are explicitly opt-in. The service combines pgvector
and PostgreSQL keyword candidates, RRF, overlap removal, a configured reranker, adaptive passages,
selective same-section neighbors, a hard context budget, and composite match confidence. Results
are exact cited excerpts with private PDF links; there is no answer generation in this task.

The durable [retrieval handoff](document-retrieval.md) contains architecture/reading order, API
schemas, source/freshness rules, scored reranker contract, configuration, failure behavior,
limits, and manual review. Migration `0013_retrieval_fts` was applied locally. It adds only a
GIN search index. `RERANKER_TIMEOUT_SECONDS` is newly required; the existing provider connection
and a configured pinned reranker snapshot are used. No new dependency/infrastructure was added.

Verification: full Python suite **256 passed**, no skips, five existing SWIG deprecation warnings.
Python lint, five chunking eval groups, five offline retrieval eval groups, web lint/TypeScript,
and webpack production build passed. Three live synthetic reranker cases passed: direct and
table matches ranked first, injection distractors scored zero, and missing evidence was below
the relevance threshold. Nine isolated Chrome checks used the real search component and mocked
API responses; the temporary harness is not an end-to-end regression suite. An initial full
run found a missing import in a new neighbor test; it was corrected before the passing full run.

Manual review: restart API after env changes, confirm/extract/index a small PDF, search a known
phrase, inspect the original page citation, and prepare/open its private PDF link. Toggle
reference editions, switch bikes, and test missing evidence/provider errors. Full signed-in
browser/database/live-provider search remains manual. Broader representative manual recall,
latency/cost, exact-spec and diagram evals are **4.5 next**. OCR/vision and real malware scanning
remain separate open follow-ups; match confidence is not calibrated mechanical correctness.

Reviewed/updated roadmap, docs index, developer guide/runbook, root/API/web/shared-library,
service/repository/test/eval READMEs, and the new retrieval guide. Existing indexing pipeline
instructions remain valid; this milestone executes search in the API and adds no worker task.

## First manual evidence evaluations (4.5) — 2026-09-11

Implemented for the current retrieval scope. Twelve fixed cases cover source-backed torque,
capacity conditions, maintenance intervals, table row distinctions, synthetic diagram location
and pending content, missing specifications, instruction attacks, and owner isolation. Numeric
facts are short paraphrases with original Honda manual page attribution. They are not copied
PDF pages or complete repair procedures. See the [standalone handoff](manual-evaluations.md).

`evals/manual_corpus.py` generates small fixture PDFs, runs actual extraction/chunking, and
inserts isolated database rows inside an always-rolled-back transaction. `evals/manuals.py`
calls the real retrieval service/repository, compares independent gold cases, and reports recall,
provenance, context size, latency, and provider calls. Default mode replays real recorded vectors
and scores without provider calls. Live mode uses existing ports. CI now runs this separate gate
against migrated PostgreSQL, and lints eval modules. Missing DB/replay data fails the gate.

Verification: **12/12 live and 12/12 replay cases passed**, eight positive cases with candidate
and final source recall 1.0 on this small corpus. Negative/visual/ownership outcomes matched their
expectations. The passing live run used 22 provider calls; model-using searches had median
1,719 ms and maximum 3,369 ms. The [live report](../evals/reports/manual-baseline-2026-09-11.json)
is checked in. An initial caption comparison failed on a PDF line break; whitespace-normalized
gold matching fixed it while exact source-span checks stayed verbatim. The live suite was rerun
before recording. Grader mutation tests and forced-exception database rollback passed.

Full Python suite: **265 passed**, no skips, five existing SWIG deprecation warnings. Python lint,
existing chunking/retrieval offline gates, and diff/documentation checks passed. No web build
was rerun: this task changes evaluation tooling/CI/documentation, with no UI or production API
changes. No migration, environment key, dependency, infrastructure, worker, or storage changes.

Read the case manifest → corpus builder → runner/grader → replay/report files. To review, run
`PYTHONPATH=libs:services/api .venv/bin/python -m evals.manuals` against local migrated PostgreSQL.
Inspect expected pages/conditions and test a deliberately wrong returned citation in the grader
tests. Only regenerate provider observations explicitly after reviewing failures; never change
gold answers to accommodate a model mistake.

This is a first, small suite for one stock model, not a broad full-manual benchmark. Visual
understanding and generated-answer withholding are explicitly unevaluated because those product
capabilities are pending. Cost/token instrumentation and broader conflict/applicability evals
remain open. OCR/vision and real malware scanning remain separate follow-ups. Next numbered
work is **5.1**. Updated roadmap, docs index, developer guide/runbook, root/API/test/eval READMEs,
retrieval handoff, and dedicated eval guide; other subsystem behavior/setup is unchanged.

## Conversations (5.1) — 2026-09-16

Status: **implemented** for conversation storage only. Users can create bike-scoped threads,
append messages, switch bike context (recording a context boundary), refresh a deterministic
rolling summary, and delete conversation content. There is still no ReasoningAgent, tool calling,
compact context pack, citations, or assistant replies.

Architecture: Next proxies → `routes/conversations.py` → `ConversationService` →
`ConversationRepository` → Postgres. Bike ownership is checked through `BikeRepository` before
create/list/switch. Messages stamp `bike_context_id` from `current_bike_id`. Rolling summary is
a bounded recent-turn compression (`deterministic-v1`); LLM `SUMMARY_MODEL` refresh is deferred.

Files to read, in order:

1. `services/api/app/models/conversation.py` — tables/enums
2. `services/api/alembic/versions/0014_conversations.py` — migration
3. `services/api/app/repositories/conversations.py` — owner-scoped queries
4. `services/api/app/services/conversations.py` — create/list/get/append/switch/delete + summary
5. `services/api/app/routes/conversations.py` — HTTP contract
6. `apps/web/components/AssistantWorkspace.tsx` — minimal UI
7. `tests/unit/test_conversations.py` and `tests/api/test_conversations_http.py`

Security and failure behavior: foreign conversation/bike ids return the same not-found path;
empty messages are rejected; delete removes messages and boundaries with the conversation;
routes do not log message bodies.

Verification actually run:

- `python -m pytest tests/unit/test_conversations.py tests/api/test_conversations_http.py -q`
  — 6 passed
- `alembic upgrade head` applied `0014_conversations`
- `python -m pytest tests/integration/test_conversation_repository.py -q` — 1 passed
- `ruff check` on new conversation modules — passed
- `npx tsc --noEmit -p apps/web/tsconfig.json` — passed
- Combined conversation suite after list-filter fix — 7 passed

Manual review: open `/assistant` with an active bike, create a thread, send a user message,
switch bike context, confirm a boundary and rolling summary appear, delete the thread.

Migrations: `0014_conversations`. Environment variables: none added. Dependencies: none added.
Unresolved at time of 5.1: agent replies, compact context, tools, citations, hierarchical memory,
polished UI. Compact context is now covered in 5.2 below.

## Compact context (5.2) — 2026-09-16

Status: **implemented** for always-load context assembly. `CompactContextService.build` returns a
bounded pack from the conversation’s current bike plus recent turns and rolling summary.
Modifications, maintenance, and ride slices are explicit stubs (`available: false`,
`reason: domain_not_implemented`) until Phases 6–7. On-demand manuals use
`CompactContextService.search_manuals` → `RetrievalService.search` (no new HTTP; existing
`POST /v1/retrieval` remains).

Architecture: Assistant panel → Next proxy → `GET /v1/conversations/{id}/context` →
`CompactContextService` → `ConversationService` + `BikeRepository`.

Files to read, in order:

1. `services/api/app/services/compact_context.py` — pack types, budget, build, manuals helper
2. `services/api/app/routes/conversations.py` — context response schema/route
3. `apps/web/app/api/conversations/[conversationId]/context/route.ts`
4. `apps/web/components/AssistantWorkspace.tsx` — always-loaded context panel
5. `tests/unit/test_compact_context.py` / `tests/api/test_compact_context_http.py`

Security: owner-scoped conversation and bike lookups; foreign ids return not-found. No full
message logging.

Verification actually run:

- `python -m pytest tests/unit/test_compact_context.py tests/api/test_compact_context_http.py -q`
  — 5 passed
- `ruff check` on new/changed modules — passed
- `npx tsc --noEmit -p apps/web/tsconfig.json` — passed

Manual review: open a thread on `/assistant`, expand “Always-loaded context”, confirm bike
identity/hours and deferred domain stubs.

Migrations: none. Environment variables: none. Dependencies: none.
Unresolved: agent tools (5.3), write policy (5.4), citations/safety (5.5), hierarchical memory
(5.6), polished UI (5.7), real mods/maintenance/ride slices when those domains land.

Next numbered task is **5.3**.

## Assistant tools (5.3) — 2026-09-17

Status: **implemented** for read-only tool adapters. `ToolRegistry` exposes
`get_bike`, `get_compact_context`, `search_manuals`, and `get_conversation`. Each handler calls
the same domain services HTTP uses. The registry refuses mutating tool registration until write
policy (5.4). There is still no ReasoningAgent / ChatModel tool-calling loop.

Architecture: future agent → `ToolRegistry.invoke` → domain service → repository → Postgres.

Files to read, in order:

1. `services/api/app/assistant_tools/types.py` — ToolSpec / ToolContext / ToolResult
2. `services/api/app/assistant_tools/registry.py` — register / list / invoke
3. `services/api/app/assistant_tools/read_tools.py` — handlers
4. `services/api/app/assistant_tools/factory.py` — default registry
5. `tests/unit/test_assistant_tools.py`

Security: ownership stays in BikeService / ConversationService / CompactContextService; tools map
not-found the same way HTTP does. No write tools exist, so casual oil-change talk cannot mutate.

Verification actually run:

- `python -m pytest tests/unit/test_assistant_tools.py -q` — 3 passed
- `ruff check` on assistant_tools / deps / tests — passed

Migrations: none. Environment variables: none. Dependencies: none.
Unresolved: write policy + confirmations (5.4), citations/safety (5.5), hierarchical memory (5.6),
agent loop / ChatModel tools, polished UI (5.7).

Next numbered task is **5.4**.

## Write policy (5.4) — 2026-09-17

Status: **implemented** as a policy framework on the assistant tool registry. Mutating tools must
declare `write_class` (`auto` or `confirm`). Before invoke, the registry checks `FLAG_AI_WRITES`
and, for confirm-class tools, requires `ToolContext.confirmed` or
`ToolContext.explicit_instruction`. Casual mentions without those flags get
`confirmation_required`. The default registry still registers only read tools — durable machine
writes wait for maintenance/mods/hours domain services.

Files to read, in order:

1. `services/api/app/assistant_tools/write_policy.py`
2. `services/api/app/assistant_tools/registry.py`
3. `services/api/app/assistant_tools/types.py`
4. `tests/unit/test_write_policy.py`

Verification actually run:

- `python -m pytest tests/unit/test_write_policy.py tests/unit/test_assistant_tools.py -q`
  — 7 passed
- `ruff check` on assistant_tools / related tests — passed

Migrations: none. Environment variables: none (uses existing `FLAG_AI_WRITES`). Dependencies: none.
Unresolved: real mutating tools, confirmation UI, utterance classification NLP, citations (5.5),
agent loop, hierarchical memory (5.6), polished UI (5.7).

Next numbered task is **5.5**.

## Citations and safety (5.5) — 2026-09-17

Status: **implemented** as answer-policy helpers (no answer generator). `citations.py` shapes
layered Sources citations from retrieval passages and decides:

- authoritative source found → provide exact value with citation
- no source + safety/engine-critical → withhold exact number (+ escalate as unverifiable critical)
- no source + lower risk → labeled non-authoritative guidance only
- mechanic escalation only for locked risk reasons (not difficulty alone)

Files to read, in order:

1. `services/api/app/assistant_tools/citations.py`
2. `tests/unit/test_citations_safety.py`
3. DESIGN §7 / §13 (local) for the LOCKED rules this encodes

Verification: `python -m pytest tests/unit/test_citations_safety.py -q` — 5 passed; ruff passed.
Migrations/env/deps: none. Unresolved: ReasoningAgent that calls these helpers, UI source chips
(5.7), hierarchical memory (5.6).

Next numbered task is **5.6**.

## AssistantWorkspace CI lint fix — 2026-09-17

Status: **fixed**. Website CI failed on `react-hooks/set-state-in-effect` in
`AssistantWorkspace.tsx` (sync clears when `!activeBike` / `!selectedId`). The workspace now
splits empty-bike UI from a bike-keyed `AssistantBikeWorkspace`, derives inactive detail from
`selectedId`, and only fetches when a bike/thread is present (same pattern as DocumentLibrary).

Verification: `cd apps/web && npm run lint` — passed.

## Hierarchical memory (5.6) — 2026-09-22

Status: **implemented** as selective long-term conversation memory (no agent loop).

`HierarchicalMemoryService` searches rolling summaries for an owned bike (hard filter), ranks
hits with deterministic token overlap (`token_overlap_v1`), optionally excludes the current
thread, then expands a contiguous raw-message window around the best-matching turns (count +
char budgets). Tools `search_conversation_memory` and `expand_conversation_memory` wrap the
same service. Durable bike facts still live in structured tables, not opaque AI memory.

Files to read, in order:

1. `services/api/app/services/hierarchical_memory.py` — ranking, expand, ownership
2. `services/api/app/assistant_tools/read_tools.py` — memory tool adapters
3. `tests/unit/test_hierarchical_memory.py` and `tests/unit/test_assistant_tools.py`
4. DESIGN §5 (local) for LOCKED short-term vs long-term rules

Rules: bike hard filter; owner isolation via `ConversationService`; empty/invalid queries fail;
summary embeddings / semantic ranking deferred (service remains the entry point).

Verification:
` .venv/bin/python -m pytest tests/unit/test_hierarchical_memory.py tests/unit/test_assistant_tools.py tests/unit/test_write_policy.py -q`
— 14 passed; ruff clean on touched files.

Migrations/env/deps: none. Manual review: create two threads on one bike with distinct topics,
invoke search excluding the current id, expand the hit, confirm foreign bike/user denied.

Unresolved: semantic summary embeddings, ReasoningAgent loop (UI polish done in 5.7).

## Assistant UI polish (5.7) — 2026-09-22

Status: **implemented** as presentation polish (still no ReasoningAgent replies).

- Role-styled chat bubbles and auto-scroll in `AssistantWorkspace`
- Composer attach control remains disabled (later attachments) with clearer labels
- `AssistantSources` renders expandable source chips matching 5.5 citation payloads when a
  message includes `citations`
- Shell `AssistantFab` keeps quick entry off `/assistant` with an explicit aria-label
- Page disclaimer notes cite/withhold behavior

Files to read, in order:

1. `apps/web/components/AssistantSources.tsx`
2. `apps/web/components/AssistantWorkspace.tsx`
3. `apps/web/components/AssistantFab.tsx`
4. `apps/web/app/(shell)/assistant/page.tsx`
5. `apps/web/app/globals.css` (assistant / composer / sources / FAB)

Verification: `cd apps/web && npm run lint` — passed. Migrations/env/deps: none.

Manual review: from a non-assistant page open the FAB → `/assistant`; send a user message;
confirm disclaimer under the panel; note Sources only appear when citation payloads exist.

Unresolved: agent loop that produces assistant messages + citations; attachment button.

Next: **Phase 6** (maintenance/engine hours) unless ReasoningAgent is prioritized first.
