import json

import httpx
import pytest

from vroometr.ai.embeddings import EmbeddingFailed, OpenAIEmbeddingModel, validate_vectors


def adapter(handler):
    return OpenAIEmbeddingModel(
        api_key="test-key",
        base_url="https://embedding.invalid/v1",
        model="fixture-model",
        timeout=1,
        transport=httpx.MockTransport(handler),
    )


def test_embedding_adapter_validates_and_orders_response():
    def handler(request):
        body = json.loads(request.content)
        assert body["dimensions"] == 1536 and body["encoding_format"] == "float"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(
            200,
            json={
                "model": "fixture-model",
                "data": [
                    {"index": 1, "embedding": [0.2] * 1536},
                    {"index": 0, "embedding": [0.1] * 1536},
                ],
            },
        )

    assert adapter(handler).embed(["first", "second"])[0][0] == 0.1


@pytest.mark.parametrize(
    "payload",
    [
        {"model": "wrong", "data": []},
        {"model": "fixture-model", "data": [{"index": 0, "embedding": [1]}]},
        {"model": "fixture-model", "data": [{"index": 1, "embedding": [1] * 1536}]},
        {"model": "fixture-model", "data": [{"index": True, "embedding": [1] * 1536}]},
    ],
)
def test_rejects_invalid_provider_data(payload):
    with pytest.raises(EmbeddingFailed):
        adapter(lambda request: httpx.Response(200, json=payload)).embed(["text"])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, 1e39])
def test_rejects_invalid_vector_values(bad):
    with pytest.raises(EmbeddingFailed):
        validate_vectors([[bad] * 1536], 1)


def test_provider_failure_does_not_expose_payload():
    with pytest.raises(EmbeddingFailed) as caught:
        adapter(lambda request: httpx.Response(429, text="secret provider payload")).embed(["text"])
    assert "payload" not in str(caught.value)
    with pytest.raises(EmbeddingFailed):
        adapter(lambda request: None).embed(["x" * 1201])
