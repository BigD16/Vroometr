"""Versioned retrieval baselines; source passages are never rewritten or cut mid-span."""

import re
from dataclasses import dataclass

from app.retrieval.types import Candidate, Passage
from vroometr.ai.ports import RankedPassage

RETRIEVAL_VERSION = "hybrid-v1"
CONTEXT_CHAR_LIMIT = 8000
MAX_PASSAGES = 8
MIN_RELEVANCE = 0.45


@dataclass(frozen=True)
class Fused:
    passage: Passage
    rrf: float
    vector_score: float
    dual_match: bool


@dataclass(frozen=True)
class Match:
    passage: Passage
    relevance: float
    confidence: float
    role: str = "match"
    neighbor_of: str | None = None


def terms(query: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", query.lower()))


def overlaps(a: Passage, b: Passage) -> bool:
    if a.content_hash == b.content_hash:
        return True
    if a.source_hash != b.source_hash:
        return False
    return any(
        x["page_index"] == y["page_index"]
        and max(x["start_char"], y["start_char"]) < min(x["end_char"], y["end_char"])
        for x in a.source_span
        for y in b.source_span
    )


def fuse(vector: list[Candidate], keyword: list[Candidate]) -> list[Fused]:
    scores, passages, vector_scores, occurrences = {}, {}, {}, {}
    for source, candidates in enumerate((vector, keyword)):
        seen = set()
        for rank, candidate in enumerate(candidates, 1):
            key = candidate.passage.id
            if key in seen:
                continue
            seen.add(key)
            passages[key] = candidate.passage
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
            occurrences[key] = occurrences.get(key, 0) + 1
            if source == 0:
                vector_scores[key] = candidate.score
    ranked = sorted(scores, key=lambda key: (-scores[key], not passages[key].is_primary, str(key)))
    result = []
    for key in ranked:
        passage = passages[key]
        duplicate = next(
            (i for i, item in enumerate(result) if overlaps(item.passage, passage)), None
        )
        fused = Fused(passage, scores[key], vector_scores.get(key, 0), occurrences[key] == 2)
        if duplicate is None:
            result.append(fused)
        elif passage.is_primary and not result[duplicate].passage.is_primary:
            # Preserve manufacturer authority when identical/overlapping editions collide.
            result[duplicate] = fused
    return sorted(result, key=lambda item: (-item.rrf, str(item.passage.id)))[:40]


def select_matches(
    query: str, candidates: list[Fused], ranking: list[RankedPassage]
) -> list[Match]:
    eligible = [row for row in ranking if row.score >= MIN_RELEVANCE]
    selected = eligible[:5]
    if len(selected) == 5:
        selected += [row for row in eligible[5:8] if row.score >= selected[4].score - 0.08]
    query_terms = terms(query)
    result = []
    for row in selected:
        candidate = candidates[row.index]
        coverage = len(query_terms & terms(candidate.passage.text)) / max(1, len(query_terms))
        confidence = (
            0.65 * row.score
            + 0.20 * max(0, min(1, candidate.vector_score))
            + 0.10 * candidate.dual_match
            + 0.05 * coverage
        )
        result.append(Match(candidate.passage, row.score, round(confidence, 4)))
    return result


def useful_neighbor(base: Passage, neighbor: Passage) -> bool:
    if base.document_id != neighbor.document_id or base.section_id != neighbor.section_id:
        return False
    delta = neighbor.section_chunk_index - base.section_chunk_index
    if delta == -1:
        return base.text[:1].islower() or bool(re.match(r"^(This|These|Then|It)\b", base.text))
    if delta == 1:
        return bool(base.text) and base.text.rstrip()[-1] not in ".!?。！？"
    return False


def within_budget(matches: list[Match], neighbors: list[Match]) -> list[Match]:
    result, size = [], 0
    for item in [*matches, *neighbors]:
        if len(result) >= MAX_PASSAGES:
            break
        if item.neighbor_of and item.neighbor_of not in {str(m.passage.id) for m in result}:
            continue
        if size + len(item.passage.text) > CONTEXT_CHAR_LIMIT:
            continue
        if any(overlaps(item.passage, existing.passage) for existing in result):
            continue
        result.append(item)
        size += len(item.passage.text)
    return result
