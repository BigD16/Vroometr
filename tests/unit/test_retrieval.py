import pytest
from app.services.retrieval import InvalidSearch, RetrievalService


@pytest.mark.parametrize(
    "query,refs", [("", False), ("  ", False), ("x" * 1201, False), (None, False), ("test", "true")]
)
def test_service_rejects_invalid_search_before_reading_or_calling_providers(query, refs):
    service = RetrievalService(None, None, None, None, reranker_model="fixture")
    with pytest.raises(InvalidSearch):
        service.search(None, None, query, refs)
