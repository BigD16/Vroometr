import json

import httpx
import pytest

from vroometr.ai.ports import RankedPassage
from vroometr.ai.reranking import OpenAIReranker, RerankingFailed, validate_ranking


def adapter(payload=None, status=200, inspect=None):
    def handle(request):
        if inspect:
            inspect(json.loads(request.content))
        return httpx.Response(status, json=payload)

    return OpenAIReranker(
        api_key="fixture-secret",
        base_url="https://fixture.invalid/v1",
        model="fixture-snapshot",
        timeout=1,
        transport=httpx.MockTransport(handle),
    )


def payload(rows):
    return {
        "model": "fixture-snapshot",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"scores": rows})}],
            }
        ],
    }


def test_provider_preserves_indexes_and_uses_strict_untrusted_input_contract():
    captured = []
    result = adapter(
        payload([{"index": 0, "score": 0.1}, {"index": 1, "score": 0.9}]), inspect=captured.append
    ).rerank("query", ["unrelated", "relevant"])
    assert result == [RankedPassage(1, 0.9), RankedPassage(0, 0.1)]
    request = captured[0]
    assert request["store"] is False and request["text"]["format"]["strict"] is True
    assert "untrusted" in request["instructions"] and "tools" not in request
    assert json.loads(request["input"])["passages"][1] == {"index": 1, "text": "relevant"}


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [RankedPassage(0, 1), RankedPassage(0, 1)],
        [RankedPassage(True, 0.5), RankedPassage(0, 0.5)],
        [RankedPassage(0, float("nan")), RankedPassage(1, 0.5)],
        [RankedPassage(0, True), RankedPassage(1, 0.5)],
        [RankedPassage(0, 1.1), RankedPassage(1, 0.5)],
    ],
)
def test_invalid_rankings_fail_closed(rows):
    with pytest.raises(RerankingFailed):
        validate_ranking(rows, 2)


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"status": "incomplete"},
        {"status": "completed", "model": "different", "output": []},
        {
            "status": "completed",
            "model": "fixture-snapshot",
            "output": [
                {"type": "message", "content": [{"type": "refusal", "refusal": "fixture-secret"}]}
            ],
        },
        payload([{"index": 2, "score": 0.9}]),
    ],
)
def test_missing_refused_or_malformed_outputs_are_unavailable(data):
    with pytest.raises(RerankingFailed) as caught:
        adapter(data).rerank("query", ["source"])
    assert "fixture-secret" not in str(caught.value)


def test_provider_error_and_input_bounds():
    with pytest.raises(RerankingFailed):
        adapter({"error": "fixture-secret"}, 429).rerank("query", ["source"])
    with pytest.raises(RerankingFailed):
        adapter().rerank("x" * 1201, ["source"])
    with pytest.raises(RerankingFailed):
        adapter().rerank("query", ["source"] * 41)


def test_configured_factory_and_missing_settings(monkeypatch):
    from pydantic import SecretStr

    from vroometr.ai.factory import get_reranker
    from vroometr.ai.unconfigured import UnconfiguredReranker
    from vroometr.settings import settings

    monkeypatch.setattr(settings, "openai_api_key", SecretStr("fixture"))
    monkeypatch.setattr(settings, "openai_base_url", "https://fixture.invalid/v1")
    monkeypatch.setattr(settings, "reranker_model", "fixture")
    assert isinstance(get_reranker(), OpenAIReranker)
    monkeypatch.setattr(settings, "reranker_model", "")
    assert isinstance(get_reranker(), UnconfiguredReranker)
