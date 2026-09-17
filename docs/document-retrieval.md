# Document retrieval — roadmap 4.4

Implemented 2026-09-11. Documents now offers **Search bike documents** over confirmed,
indexed sources belonging to the signed-in account and selected bike. Results contain exact
source excerpts with PDF page/section citations. This milestone does not generate answers,
verify mechanical claims, or resolve disagreements between editions. Task 4.5 now adds [first source-backed retrieval evals](manual-evaluations.md);
the text assistant is Phase 5.

## Reading order and data flow

1. [HTTP route](../services/api/app/routes/retrieval.py): authenticated request/response schemas,
   dependency assembly, and error mapping. The web [proxy](../apps/web/app/api/retrieval/route.ts)
   uses the existing Clerk-to-FastAPI forwarding path.
2. [RetrievalService](../services/api/app/services/retrieval.py): validates the search, checks bike
   ownership before provider calls, orchestrates retrieval/ranking/context, and revalidates sources.
   Future assistant tools must call this same service.
3. [RetrievalRepository](../services/api/app/repositories/retrieval.py): one `_eligible` predicate
   shared by vector, keyword, neighbor, and final reads. PostgreSQL remains the only search store.
4. [Ranking rules](../services/api/app/retrieval/ranking.py): RRF, overlap removal, adaptive selection,
   useful neighbors, whole-passage budget, and confidence. [Passage](../services/api/app/retrieval/types.py)
   is a source snapshot; `Match` adds scores and the match/neighbor role.
5. [Reranker adapter](../libs/vroometr/ai/reranking.py) and
   [ports/factories](../libs/vroometr/ai/factory.py): strict scored output over the existing OpenAI
   connection. `Reranker.rerank` now returns `RankedPassage(index, score)` entries instead of strings.
   It must return every input index once, with a finite score between zero and one. This preserves
   source identity without asking a model to copy or rewrite source passages.
6. [DocumentSearch](../apps/web/components/DocumentSearch.tsx): accessible search form, explicit
   reference scope, loading/empty/error states, plain-text excerpts, partial-source labels, and
   private PDF access. Mounted in the active-bike Documents workspace.

Flow: authenticated request → owner check → query embedding → vector + PostgreSQL keyword
search → RRF → deduplicate → rerank → adaptive matches → selected neighbors → hard budget →
source revalidation → cited excerpts. It runs synchronously in the API; no new worker or
infrastructure is required. Index construction still uses the existing Celery pipeline.

## Search and source rules

Default scope is the active primary manufacturer manual plus active supporting documents.
`include_reference_editions: true` additionally allows other confirmed active/archived editions.
Unconfirmed drafts are excluded in both scopes. Response citations retain document type,
revision, primary status, and archived status. Exact duplicates may prefer a primary-manual
citation; this does not merge documents or hide conflicting text with different source bytes.
Reference-mode results require the caller to assess applicability and disagreements.

Every repository read requires the bike and attachment owner to match the authenticated account,
verified upload status, non-infected attachment, confirmed document, usable completed/partial
extraction and index, matching extraction attempt, current chunking version, configured embedding
model/version, a non-null embedding, completed source page, and consistent source hashes and
stored page/span extraction versions. Partial documents remain usable only through eligible
chunks and are labeled incomplete. Pages pending OCR/vision are not searched.

Scalar snapshots are read again before reranking and after ranking/neighbor selection. Changed
or inaccessible candidates are removed before reranking. If any final passage changed, the whole
response returns `sources_changed` without passages. This covers re-extraction, rebuilding,
deletion, infection, and source metadata changes. It is a check at request time, not push-based
revocation of text already displayed in a browser. No database locks span model calls.

The file scanner remains **unconfigured**: non-infected is not a claim that malware scanning
passed. Real scanning is the separately planned 3.4 follow-up. Private PDF viewing reuses the
owner-authorized 60-second access endpoint. The UI prepares a link, then lets the reader open
it at the original page. Unlinking an attachment from a bike does not delete its document record;
existing document ownership/lifecycle rules still apply.

## Versioned baseline and limits

`hybrid-v1` uses at most 50 vector and 50 keyword candidates. Vector retrieval is exact cosine
search over eligible rows; keyword search uses an English `to_tsvector` GIN index and
`websearch_to_tsquery`, OR-ing sanitized query words for recall. No approximate vector index is
introduced before evaluating its effect on filtered recall.

RRF uses `1 / (60 + rank)` per candidate list. Deduplication removes exact content hashes and
intersecting character spans on the same source-hash/page. Up to 40 candidates reach the reranker.
Scores below 0.45 are excluded. Normally five matches are kept; up to three more qualify when
within 0.08 of the fifth score. Same-section ±1 neighbors are added only for a leading
continuation cue or an unfinished trailing sentence/colon. Neighbors preserve their own citation
and point to their base match. Complete statements do not automatically expand.

Final context has at most eight passages **including neighbors**, and at most 8,000 source-text
characters. Matches take priority over neighbors. Whole passages are dropped to fit; spans are
never sliced mid-procedure. This is a character cap, not a tokenizer-specific token count.

Confidence combines reranker relevance (65%), nonnegative cosine similarity (20%), agreement
between both candidate lists (10%), and query-word coverage (5%). It is an uncalibrated match
estimate, not a probability that a mechanical statement is correct. The response reports
candidate counts, version names, elapsed milliseconds, context size, and confidence; it does not
log queries or excerpts. Per-request provider token usage/cost and representative recall metrics
are not instrumented yet. These constants and the initial reranker choice remain benchmark
baselines; change them with eval evidence.

## API

`POST /v1/retrieval` (web proxy: `POST /api/retrieval`):

```json
{"bike_id":"<owned-bike-uuid>","query":"inspection checklist","include_reference_editions":false}
```

Query must contain non-whitespace text and be at most 1,200 characters. Extra fields are rejected;
reference scope is a strict boolean. The server derives identity from authentication.

Success contains `status`, `passages`, `include_reference_editions`, and `diagnostics`.
Each passage entry includes `passage` (IDs, exact text, file/page/section/span/hash and edition
metadata, index attempt, incomplete flag), `relevance`, `confidence`, `role`, and `neighbor_of`.
Pages are zero-based in the API and one-based in the UI. Character spans are end-exclusive.
The OpenAPI response schema documents these fields.

Statuses: `ready`, `no_indexed_sources`, `no_relevant_evidence`, or `sources_changed`.
No eligible sources returns without a provider call. HTTP errors: 401 for unauthenticated,
404 for an unknown/foreign bike, 422 for invalid input, 503 for missing configuration or provider
failure. A missing/failed reranker never silently falls back to unranked vector/keyword results.
Provider refusals, incomplete responses, mismatched model identity, duplicate/missing indexes,
and invalid scores fail closed. Model input is untrusted data; the reranker receives no tools,
generates only scores, and cannot change stored source passages or execute writes.

## Configuration and migration

Apply migration `0013_retrieval_fts` with `alembic upgrade head` from `services/api`. It adds a
GIN full-text expression index to `document_chunks`; no document rows are rewritten. It was
applied locally. Downgrade removes only that index. No new dependency is added for 4.4.

Root `.env` owns `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_VERSION`,
`EMBEDDING_TIMEOUT_SECONDS`, `RERANKER_MODEL`, and the new required `RERANKER_TIMEOUT_SECONDS`.
`.env.example` lists names with empty values. The local reranker uses a pinned model snapshot
with Responses structured-output support; the embedding key/connection is reused. The adapter
requires the returned model identity to equal the configured model, so prefer snapshots to aliases.
The exact initial choice remains provisional pending representative benchmarks. Restart the API
after environment changes. Changing the reranker does not require rebuilding embeddings;
changing the embedding model/version does.

Provider references: [Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[initial model capabilities](https://developers.openai.com/api/docs/models/gpt-4.1-mini), and
[PostgreSQL text-search controls](https://www.postgresql.org/docs/16/textsearch-controls.html).

## Verification and manual review

- Full Python suite: **256 passed**, no skips, five existing PyMuPDF/SWIG deprecation warnings.
  [Database tests](../tests/integration/test_retrieval_db.py) exercise real pgvector/FTS, scope,
  stale/infected/deleted sources, partial labels, neighbor boundaries, and changes during calls.
  [API tests](../tests/api/test_retrieval_http.py),
  [adapter tests](../tests/unit/test_reranking.py), and
  [input tests](../tests/unit/test_retrieval.py) use controlled provider responses.
- [Retrieval evals](../evals/retrieval.py): five offline baseline groups plus three optional live
  synthetic cases. Live direct-match/table candidates scored 1, injection distractors 0, and
  the missing-specification case stayed below 0.45. No uploaded documents were sent. This small
  eval set does not establish real-manual recall, diagram understanding, or answer safety.
- Python lint, existing five chunking evals, web lint, TypeScript, and webpack production build
  passed. Nine isolated Chrome checks passed using the actual component with mocked APIs:
  empty state, scope, escaped text/citation, partial warning, PDF link, missing evidence, error
  clearing, loading, and bike-switch race handling. This temporary harness is not a checked-in
  end-to-end suite; full signed-in browser → database → live-provider search remains manual.

Run offline gates from the repository root:

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.chunking
PYTHONPATH=libs:services/api .venv/bin/python -m evals.retrieval
```

`--live` on the retrieval command makes three small paid provider requests using synthetic text.
It is opt-in; CI runs offline evals only.

Manual review: restart the API, select a bike, and open Documents. Confirm, extract, and index
a small PDF. Search a phrase visible in its text, inspect the page/section citation, and open
the PDF. Search for absent information. Switch bikes, toggle reference editions, rebuild an
index, and retry search to check scope/freshness. Try an unavailable provider and verify a
recoverable error clears prior results. The [4.5 suite](manual-evaluations.md) now adds source-backed fixtures and initial recall/latency
measurements. Full-manual scale/cost, OCR/vision, and actual malware scanning remain separate work.
