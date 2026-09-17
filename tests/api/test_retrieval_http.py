from uuid import uuid4

from app.deps import get_current_user
from app.main import create_app
from app.models.user import User
from app.routes.retrieval import get_retrieval_service
from app.services.bikes import BikeNotFound
from app.services.retrieval import InvalidSearch
from fastapi.testclient import TestClient

from vroometr.ai.reranking import RerankingFailed
from vroometr.ai.unconfigured import UnconfiguredError


def test_search_identity_validation_and_provider_errors():
    owner = User(id=uuid4())
    calls = []
    failure = None

    class Service:
        def search(self, user_id, bike_id, query, references):
            calls.append((user_id, bike_id, query, references))
            if user_id != owner.id:
                raise BikeNotFound
            if failure:
                raise failure
            return {
                "status": "no_indexed_sources",
                "passages": [],
                "include_reference_editions": references,
                "diagnostics": {
                    "vector_candidates": 0,
                    "keyword_candidates": 0,
                    "reranker_candidates": 0,
                    "retrieval_version": "fixture",
                    "reranker_version": "fixture",
                    "reranker_model": "fixture",
                    "embedding_model": "fixture",
                    "embedding_version": "fixture",
                    "elapsed_ms": 0,
                    "context_chars": 0,
                    "confidence": 0,
                    "confidence_is_calibrated": False,
                },
            }

    app = create_app()
    app.dependency_overrides[get_retrieval_service] = Service
    client = TestClient(app)
    body = {"bike_id": str(uuid4()), "query": "test"}
    assert client.post("/v1/retrieval", json=body).status_code == 401
    app.dependency_overrides[get_current_user] = lambda: User(id=uuid4())
    assert client.post("/v1/retrieval", json=body).status_code == 404
    app.dependency_overrides[get_current_user] = lambda: owner
    assert client.post("/v1/retrieval", json=body).status_code == 200
    assert calls[-1][0] == owner.id and calls[-1][3] is False
    for extra in (
        {"query": ""},
        {"query": "x" * 1201},
        {"user_id": str(owner.id)},
        {"include_reference_editions": "true"},
        {"bike_id": "invalid"},
    ):
        assert client.post("/v1/retrieval", json={**body, **extra}).status_code == 422
    for failure, expected in [
        (InvalidSearch("query required"), 422),
        (UnconfiguredError("internal"), 503),
        (RerankingFailed("private"), 503),
    ]:
        response = client.post("/v1/retrieval", json=body)
        assert response.status_code == expected and "private" not in response.text
