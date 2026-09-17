# First manual evidence evaluations — 4.5

Implemented 2026-09-11 for the current retrieval capability. Twelve fixed cases exercise torque,
service versus disassembly capacity, maintenance conditions, front/rear table rows, diagram
location, pending visual content, missing specifications, instruction attacks, and ownership.
The numeric fixtures are short factual paraphrases grounded in Honda's
[2021 CRF250F US/Canada owner's manual](https://cdn.powersports.honda.com/documentum/MWOM/ml.remawmom.2021_31k99q20_crf250f.pdf).
They are evaluation evidence, not complete instructions for working on a motorcycle.

## Reading order

1. [Case manifest](../evals/fixtures/manual_cases.json): source URL, review date, original printed
   and PDF page references, independently written questions, expected evidence, values/units,
   and conditions. Synthetic diagram/injection entries have no manufacturer page attribution.
2. [Corpus builder](../evals/manual_corpus.py): generates small PDFs in memory, then runs the
   actual PyMuPDF extraction/routing and section/chunk builder. It inserts isolated owner/bike,
   document, page, index, and vector fixtures in a transaction that always rolls back.
3. [Runner and grader](../evals/manuals.py): calls the real `RetrievalService` and PostgreSQL
   vector/full-text repository. Measures candidate/final recall and checks returned source
   identity, exact character spans/hashes, values/units/conditions, forbidden content, missing
   evidence, context limits, and provider calls before authorization/source eligibility.
4. [Provider replay](../evals/fixtures/manual_replay.json): recorded real embedding vectors and
   reranker scores keyed by input hashes. Scores were observed from providers, not calculated
   from the expected answers. This roughly 478 KB file is intentionally separate from gold labels.
5. [Recorded live report](../evals/reports/manual-baseline-2026-09-11.json): actual per-case
   outcomes and timing. [Grader tests](../tests/unit/test_manual_eval.py) corrupt evidence to
   verify failures; [cleanup test](../tests/integration/test_manual_eval_cleanup.py) forces an
   exception and checks rollback.

The fixture PDF's pages and spans are **not** the original Honda PDF's pages/spans. The manifest
separately identifies the original source locations for reviewing paraphrased facts. No original
manual, user upload, worker task, or S3 object is created or sent by this runner. The synthetic
visual page uses abstract rectangles with no invented dimensions or mechanical specifications.

## What the gates mean

The eight positive cases all require their expected source page, including important qualifiers
such as operation type, units, front/rear position, and the earlier maintenance limit. Exact
provenance comparison stays verbatim. Gold phrase matching normalizes whitespace so PDF line
wrapping cannot produce a false failure; it does not normalize away values, units, or conditions.

Two missing-specification cases require `no_relevant_evidence` with no passages. A visual-only
bike requires `no_indexed_sources`, and a foreign owner requires `not_found`; both must avoid
provider calls. The instruction-attack page and pending visual page are forbidden in every
result. Diagram coverage verifies a searchable caption and exclusion of visual content waiting
for a provider. It does **not** claim that diagrams have been understood.

Default runs use recorded provider outputs, with real PDF processing, SQL, fusion, deduplication,
selection, neighbors, and source validation. This tests deterministic regressions, not current
provider quality. Live runs use both configured model ports and test current provider behavior.
Both modes compare output against the same independent gold manifest.

Replay checks the fixture hash, extraction/chunking/reranker versions, and reranker adapter source
hash. Unexpected text or reranker-candidate changes fail instead of inventing mock responses.
A changed model configuration requires a new live run; replay cannot evaluate a model it never
called. Recorded configuration fingerprints identify the baseline without storing environment
values. Do not regenerate a baseline merely to turn a red build green: inspect the source,
question, observed ranking, and grader failure first.

## Running and updating

Use the existing root Python environment and a migrated development PostgreSQL database
(`0013_retrieval_fts`). No new dependencies, settings, schema migrations, infrastructure, or
application endpoint changes are required.

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.manuals
```

Default replay needs no model credentials and makes no external provider calls. Missing database,
migration, fixture, or replay entries fail the command; the eval never silently skips. CI runs
this command after migrations, in addition to chunking and retrieval baseline evals.

Optional current-provider verification (paid; only checked-in fixture text is sent):

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.manuals --live --report /tmp/manual-eval-live.json
```

Use the existing embedding/reranker settings in `.env`. To deliberately replace provider
observations after reviewing changes:

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.manuals --live \
  --record evals/fixtures/manual_replay.json --report /tmp/manual-eval-live.json
```

`--record` requires `--live` and writes only when all cases pass. Gold labels are never rewritten.
Reports contain case IDs, source labels, recall, elapsed milliseconds, context size, provider
call counts, and fingerprints; they contain no credentials or private uploaded content. Failed
gates exit nonzero. Setup/provider exceptions also fail nonzero and may terminate before a JSON
report is written. All inserted evaluation database rows roll back, including on exceptions.

When adding a case: verify the manufacturer/model/year and original page; keep factual excerpts
short, retain applicability/units/conditions, and supply a distinct distractor or negative case.
Inspect new gold labels independently of provider scores. Run live, inspect the report, record a
passing baseline explicitly, then run replay. Routing or prompt changes that invalidate the tape
must be reviewed before replacement.

## Verification and limitations

- Live and replay: **12/12 passed**. All eight positive cases achieved candidate and final
  evidence recall of 1.0 on this small corpus. Both missing-spec cases returned no evidence;
  the foreign and visual-only cases made no provider calls.
- Passing live run: 22 provider calls including two indexing batches. Per-search live latency
  for model-using cases had a median of **1,719 ms** and maximum **3,369 ms**. These ten requests
  are observations, not a production latency benchmark. Token usage and monetary cost are not
  captured by the current ports; call counts are not a substitute for cost accounting.
- Eight grader unit tests pass. The full Python suite and forced-failure cleanup verification
  are recorded in the implementation progress entry. Python lint and existing offline gates
  are also required. No UI changes were made, so this task does not require a new web build.
- The first live run failed only the caption's whitespace-sensitive gold comparison. The
  checker was corrected, regression-tested, and the entire live suite rerun before recording.

This is the **first** source-backed suite, covering one model and small paraphrased text pages.
It does not establish full-manual recall, visual/table layout reconstruction, model superiority,
confidence calibration, cross-edition conflict handling, or applicability to modified bikes.
The assistant does not generate answers yet: these gates verify retrieval abstention and source
integrity, not generated-answer withholding or hallucination rates. Reports explicitly set
`answer_generation_evaluated` and `diagram_understanding_evaluated` to false. Extend these gates
when Phase 5 and OCR/vision providers exist; do not treat current passes as mechanical safety
certification. The next numbered task is 5.1; OCR/vision and actual malware scanning remain open.
