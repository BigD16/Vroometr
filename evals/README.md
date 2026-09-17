# Evals

Vroometr AI / RAG / safety evaluations.

Do not use ordinary unit tests as a substitute for these.

`chunking.py` provides offline source-integrity evals for sections/chunks:

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.chunking
```

It checks hierarchy, hard boundaries, exact spans, Unicode coverage, pending-page exclusion,
and content candidate labels. CI runs it. It does not evaluate retrieval relevance or
mechanical answers; those evals remain future work.

`retrieval.py` adds five offline baseline groups for RRF/candidate recall, duplicate/overlap
handling, adaptive depth and missing-source gating, selective neighbors/context budget, and
composite confidence. It uses deterministic scores, so it does not measure provider relevance.
CI runs it alongside chunking:

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.retrieval
```

Add `--live` to make three small paid requests through the configured reranker. These synthetic
cases check direct evidence, a text-table fixture, missing specifications, and instruction
attacks. They send no uploaded documents. The 4.5 suite below adds first source-backed retrieval checks. Broader full-manual, diagram
understanding, answer accuracy, cost, and confidence-calibration benchmarks remain future work. See the
[retrieval handoff](../docs/document-retrieval.md).

## 4.5 manual evidence suite

```bash
PYTHONPATH=libs:services/api .venv/bin/python -m evals.manuals
```

Twelve cases run actual PDF extraction/chunking and the authorized retrieval service with real
pgvector/FTS. Default providers replay recorded observations and make no API calls. The command
requires a migrated PostgreSQL database and fails if unavailable; all fixture rows roll back.
`--live` uses the configured embedding/reranker ports; `--report PATH` saves results; explicit
`--live --record PATH` saves a passing provider baseline. Gold labels remain independent.

Read the [manual eval handoff](../docs/manual-evaluations.md) for source attribution, original
versus fixture page mapping, baseline replacement rules, results, and limitations. The saved
[live report](reports/manual-baseline-2026-09-11.json) passed 12/12. This suite checks retrieval
abstention and diagram routing, not generated-answer safety or visual understanding.
