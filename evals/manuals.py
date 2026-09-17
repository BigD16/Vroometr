"""4.5 source-backed retrieval gates over real SQL and frozen/live provider responses.

Default: deterministic replay without provider calls. --live measures configured providers.
--record writes provider observations independently of gold expectations; it requires --live.
All evaluation rows are rolled back, including on failure. No S3/worker/account files are touched.
"""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.documents.chunking import CHUNKING_VERSION
from app.repositories.bikes import BikeRepository
from app.repositories.retrieval import RetrievalRepository
from app.services.bikes import BikeNotFound
from app.services.document_ingestion import PIPELINE_VERSION
from app.services.retrieval import RetrievalService
from evals.manual_corpus import corpus

from vroometr.ai.embeddings import validate_vectors
from vroometr.ai.ports import RankedPassage
from vroometr.ai.reranking import RERANKER_VERSION, validate_ranking

FIXTURES = Path(__file__).parent / "fixtures"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Embeddings:
    def __init__(self, tape, live=None):
        self.tape, self.live, self.calls = tape, live, 0

    def embed(self, texts):
        if not texts:
            return []
        self.calls += 1
        if self.live:
            vectors = validate_vectors(self.live.embed(texts), len(texts))
            for text, vector in zip(texts, vectors, strict=True):
                self.tape[digest(text)] = vector
            return vectors
        return validate_vectors([self.tape[digest(text)] for text in texts], len(texts))


class Reranker:
    def __init__(self, tape, live=None):
        self.tape, self.live, self.calls = tape, live, 0

    def rerank(self, query, passages):
        self.calls += 1
        if self.live:
            rows = validate_ranking(self.live.rerank(query, passages), len(passages))
            self.tape[digest(query)] = {digest(passages[r.index]): r.score for r in rows}
            return rows
        scores = self.tape[digest(query)]
        if set(scores) != {digest(p) for p in passages}:
            raise ValueError(
                "Reranker candidate content changed; review before recording a new baseline"
            )
        return validate_ranking(
            [RankedPassage(i, scores[digest(p)]) for i, p in enumerate(passages)], len(passages)
        )


class CandidateTrace(RetrievalRepository):
    def __init__(self, *args):
        super().__init__(*args)
        self.candidate_pages = set()

    def vector(self, *args, **kwargs):
        result = super().vector(*args, **kwargs)
        self.candidate_pages.update((c.passage.document_id, c.passage.page_start) for c in result)
        return result

    def keyword(self, *args, **kwargs):
        result = super().keyword(*args, **kwargs)
        self.candidate_pages.update((c.passage.document_id, c.passage.page_start) for c in result)
        return result


def grade(case, result, mapping, originals):
    """Gold checks consume actual service output; provider tapes never read gold labels."""
    failures = []
    matches = result.get("passages", [])
    if result["status"] != case.get("expected_status", "ready"):
        failures.append("unexpected_status")
    observed = set()
    expected_text = []
    for match in matches:
        passage = match["passage"]
        key = (passage["document_id"], passage["page_start"])
        label = mapping.get(key)
        observed.add(label)
        if label in case["expected_pages"]:
            expected_text.append(passage["text"])
        if label is None or key not in originals:
            failures.append("unknown_citation")
            continue
        page = originals[key]
        span = passage["source_span"]
        if (
            len(span) != 1
            or span[0]["page_index"] != passage["page_start"]
            or passage["page_end"] != passage["page_start"]
            or passage["source_hash"] != page.source_hash
            or span[0]["extraction_version"] != page.extraction_version
            or page.text[span[0]["start_char"] : span[0]["end_char"]] != passage["text"]
            or digest(passage["text"]) != passage["content_hash"]
            or page.state != "completed"
        ):
            failures.append("invalid_provenance")
    if not set(case["expected_pages"]).issubset(observed):
        failures.append("expected_evidence_missing")
    normalized = " ".join(" ".join(expected_text).split())
    if any(" ".join(value.split()) not in normalized for value in case.get("required_text", [])):
        failures.append("value_unit_or_condition_missing")
    if observed.intersection({"attack", "diagram_visual", *case.get("forbidden_pages", [])}):
        failures.append("forbidden_evidence")
    if not case["expected_pages"] and matches:
        failures.append("unsupported_evidence_returned")
    if len(matches) > 8 or sum(len(m["passage"]["text"]) for m in matches) > 8000:
        failures.append("context_limit_exceeded")
    return sorted(set(failures)), sorted(label for label in observed if label is not None)


def run(*, live=False, record=None, report_path=None):
    from vroometr.ai.factory import get_embedding_model, get_reranker
    from vroometr.settings import settings

    raw = (FIXTURES / "manual_cases.json").read_text()
    dataset = json.loads(raw)
    expected_meta = {
        "fixture_sha256": digest(raw),
        "chunking_version": CHUNKING_VERSION,
        "extraction_version": PIPELINE_VERSION,
        "reranker_version": RERANKER_VERSION,
        "reranker_adapter_sha256": digest(
            (Path(__file__).parents[1] / "libs/vroometr/ai/reranking.py").read_text()
        ),
    }
    if live:
        tape = {
            "metadata": {
                **expected_meta,
                "recorded_at": datetime.now(UTC).isoformat(),
                "embedding_config_sha256": digest(
                    settings.embedding_model + settings.embedding_version
                ),
                "reranker_config_sha256": digest(settings.reranker_model),
            },
            "embeddings": {},
            "rankings": {},
        }
    else:
        tape = json.loads((FIXTURES / "manual_replay.json").read_text())
        if any(tape["metadata"].get(key) != value for key, value in expected_meta.items()):
            raise ValueError(
                "Replay provenance changed; review and record a new baseline explicitly"
            )
    embedder = Embeddings(tape["embeddings"], get_embedding_model() if live else None)
    reranker = Reranker(tape["rankings"], get_reranker() if live else None)
    model, version = (
        (settings.embedding_model, settings.embedding_version) if live else ("recorded", "eval-v1")
    )
    results = []
    with corpus(dataset, embedder, model, version) as (
        session,
        user_id,
        bikes,
        mapping,
        originals,
        pending,
    ):
        repo = CandidateTrace(session, model, version)
        service = RetrievalService(
            BikeRepository(session),
            repo,
            embedder,
            reranker,
            reranker_model=settings.reranker_model if live else "recorded",
        )
        for case in dataset["cases"]:
            before = embedder.calls + reranker.calls
            repo.candidate_pages.clear()
            scope = case.get("scope", "manual")
            try:
                result = service.search(
                    uuid4() if scope == "foreign" else user_id,
                    bikes.get(scope, bikes["manual"]),
                    case["query"],
                )
            except BikeNotFound:
                result = {"status": "not_found", "passages": []}
            failures, observed = grade(case, result, mapping, originals)
            calls = embedder.calls + reranker.calls - before
            if scope in ("foreign", "visual_only") and calls:
                failures.append("provider_called_without_eligible_source")
            candidate_labels = {mapping[key] for key in repo.candidate_pages}
            expected = set(case["expected_pages"])
            candidate_recall = (
                len(expected & candidate_labels) / len(expected) if expected else None
            )
            final_recall = len(expected & set(observed)) / len(expected) if expected else None
            row = {
                "id": case["id"],
                "category": case["category"],
                "passed": not failures,
                "failures": failures,
                "status": result["status"],
                "source_pages": observed,
                "candidate_recall": candidate_recall,
                "final_recall": final_recall,
                "provider_calls": calls if live else 0,
                "elapsed_ms": result.get("diagnostics", {}).get("elapsed_ms", 0),
                "context_chars": result.get("diagnostics", {}).get("context_chars", 0),
            }
            results.append(row)
            print(json.dumps(row), flush=True)
    report = {
        "suite": dataset["version"],
        "mode": "live" if live else "recorded-replay",
        "timestamp": datetime.now(UTC).isoformat(),
        "passed": all(r["passed"] for r in results),
        "cases": results,
        "pending_visual_pages": len(pending),
        "provider_calls": embedder.calls + reranker.calls if live else 0,
        "answer_generation_evaluated": False,
        "diagram_understanding_evaluated": False,
        "metadata": tape["metadata"],
    }
    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=2) + "\n")
    # Never replace the committed baseline with a failing run.
    if record and report["passed"]:
        Path(record).write_text(json.dumps(tape, separators=(",", ":")) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--record", type=Path, help="Write a passing live provider tape to this path"
    )
    parser.add_argument("--report", type=Path, help="Write a machine-readable evaluation report")
    args = parser.parse_args()
    if args.record and not args.live:
        parser.error("--record requires --live")
    report = run(live=args.live, record=args.record, report_path=args.report)
    print(
        json.dumps(
            {"passed": report["passed"], "cases": len(report["cases"]), "mode": report["mode"]}
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
