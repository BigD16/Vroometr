# Domain services — business rules live here, not in routes.

`users.py` creates and looks up Vroometr users. `clerk_sync.py` applies Clerk `user.created` / `user.updated` by calling `ensure`. Role and entitlement never come from Clerk metadata.

`age_gate.py` decides eligibility from date of birth and versioned guardian consent. 18+ may use Vroometr directly; 13–17 need a granted consent; under-13 dates of birth are rejected and not stored.

`bikes.py` creates, lists, reads, and updates bikes for the signed-in user. Owner id always comes from the session user, never from a client-supplied `user_id`. Powertrain validation requires displacement and 2T/4T for combustion bikes, and omits both for electric bikes.

`active_bikes.py` resolves and persists the signed-in user's active bike. Selection is owner-validated; an empty or archived selection falls back to the first non-archived owned bike.

`uploads.py` validates document metadata, creates an owner-scoped pending attachment, requests
a short-lived exact-size S3 POST policy, and marks the row uploaded only after S3 metadata
verification.

`attachment_links.py` links verified uploads to owned targets. Bikes are supported now; new
domain targets must add ownership validation before becoming available. Unlinking preserves
the attachment and its other relationships.

`storage_quota.py` enforces pooled account storage before upload authorization. Pending and
uploaded persistent files reserve space; generated scenes and temporary files are excluded.
The account row lock serializes concurrent reservations with file/link mutations.

`attachments.py` lists files, authorizes short-lived private access, and handles confirmed
permanent deletion after upload-grant expiry. Storage failure preserves metadata and quota;
DB cleanup after successful object deletion can be retried. Unlinking stays a separate action.

`attachment_processing.py` queues, claims, and finishes durable attempts. Attempt IDs fence
late/duplicate worker results. Retry leases allow stalled jobs to be replaced. Queue/scanner
errors are persisted, and errors or placeholder scans cannot clear an infected verdict.
`attachments.py` rejects new access grants for infected files.

`documents.py` owns PDF record registration, metadata confirmation, duplicate warnings,
edition archiving, and primary selection. It authorizes all references, locks the account for
mutations, and rechecks file hashes before confirmation or primary selection.

`document_ingestion.py` owns confirmed-document extraction authorization, attempt claims,
leases, page provenance validation, partial completion, and fenced writes. Heavy PDF work
runs outside transactions in `pipelines/document_pipeline.py`.

`document_index.py` owns indexing prerequisites, ownership/infection checks, source-attempt
fencing, exact span validation, embedding reuse, and result state. It delegates persistence
to DocumentIndexRepository and uses the existing ingestion service for source authorization.

`retrieval.py` authorizes bike searches before model calls and orchestrates hybrid retrieval,
scored ranking, context limits, and final source validation. Future AI tools use this same
`RetrievalService.search` entry point. See [4.4](../../../../docs/document-retrieval.md).

`conversations.py` owns bike-scoped threads, message append, rolling-summary refresh, explicit
bike-switch context boundaries, and conversation deletion. Owner checks use BikeRepository.
Future assistant tools must call this same ConversationService rather than writing SQL.

`compact_context.py` assembles the always-load assistant context pack from bike identity/hours/
powertrain plus recent turns and rolling summary. Mods/maintenance/ride slices stay deferred
stubs until those domains exist. On-demand manuals call through to RetrievalService.
