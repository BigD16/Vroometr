"""Authorized hybrid retrieval shared by HTTP and future assistant tools."""

from dataclasses import asdict
from time import perf_counter

from app.retrieval.ranking import (
    RETRIEVAL_VERSION,
    Match,
    fuse,
    select_matches,
    terms,
    useful_neighbor,
    within_budget,
)
from app.services.bikes import BikeNotFound

from vroometr.ai.embeddings import validate_vectors
from vroometr.ai.reranking import RERANKER_VERSION, validate_ranking


class InvalidSearch(ValueError):
    pass


class RetrievalService:
    def __init__(self, bikes, repository, embedder, reranker, *, reranker_model):
        self.bikes, self.repository = bikes, repository
        self.embedder, self.reranker = embedder, reranker
        self.reranker_model = reranker_model

    def search(self, user_id, bike_id, query, include_reference_editions=False):
        if not isinstance(query, str) or not query.strip() or len(query) > 1200:
            raise InvalidSearch("Enter a search of 1–1200 characters.")
        if type(include_reference_editions) is not bool:
            raise InvalidSearch("Reference-edition option must be true or false.")
        if self.bikes.get(bike_id, user_id) is None:
            raise BikeNotFound
        query = query.strip()
        started = perf_counter()
        scope = (user_id, bike_id)
        refs = include_reference_editions
        stats = {"vector_candidates": 0, "keyword_candidates": 0, "reranker_candidates": 0}

        def response(status, matches=()):
            return {
                "status": status,
                "passages": [asdict(item) for item in matches],
                "include_reference_editions": refs,
                "diagnostics": {
                    **stats,
                    "retrieval_version": RETRIEVAL_VERSION,
                    "reranker_version": RERANKER_VERSION,
                    "reranker_model": self.reranker_model,
                    "embedding_model": self.repository.model,
                    "embedding_version": self.repository.version,
                    "elapsed_ms": round((perf_counter() - started) * 1000),
                    "context_chars": sum(len(item.passage.text) for item in matches),
                    "confidence": max((item.confidence for item in matches), default=0),
                    "confidence_is_calibrated": False,
                },
            }

        if not self.repository.has_sources(*scope, refs):
            return response("no_indexed_sources")
        vector = validate_vectors(self.embedder.embed([query]), 1)[0]
        semantic = self.repository.vector(*scope, vector, refs)
        # OR across sanitized words adds lexical recall for natural-language searches.
        lexical_query = " OR ".join(sorted(terms(query)))
        lexical = self.repository.keyword(*scope, lexical_query, refs) if lexical_query else []
        stats.update(vector_candidates=len(semantic), keyword_candidates=len(lexical))
        candidates = fuse(semantic, lexical)
        valid = {
            p.id for p in self.repository.revalidate(*scope, [c.passage for c in candidates], refs)
        }
        candidates = [c for c in candidates if c.passage.id in valid]
        if not candidates:
            return response("sources_changed")
        stats["reranker_candidates"] = len(candidates)
        ranking = validate_ranking(
            self.reranker.rerank(
                query,
                [f"Section: {c.passage.section_title[:200]}\n{c.passage.text}" for c in candidates],
            ),
            len(candidates),
        )
        matches = select_matches(query, candidates, ranking)
        if not matches:
            return response("no_relevant_evidence")
        neighbors = []
        for match in matches:
            for passage in self.repository.neighbors(*scope, match.passage, refs):
                if useful_neighbor(match.passage, passage):
                    neighbors.append(
                        Match(
                            passage,
                            match.relevance,
                            match.confidence,
                            "neighbor",
                            str(match.passage.id),
                        )
                    )
        selected = within_budget(matches, neighbors)
        valid = {
            p.id for p in self.repository.revalidate(*scope, [m.passage for m in selected], refs)
        }
        # A concurrent source change fails the whole result closed; never return orphan context.
        if len(valid) != len(selected):
            return response("sources_changed")
        return response("ready", selected)
