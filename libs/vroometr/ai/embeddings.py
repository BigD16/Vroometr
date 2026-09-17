"""OpenAI embedding adapter. Transport details never enter domain services."""

import math

import httpx

from vroometr.ai.unconfigured import UnconfiguredError

EMBEDDING_DIMENSIONS = 1536


class EmbeddingFailed(RuntimeError):
    pass


def validate_vectors(vectors, count: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != count:
        raise EmbeddingFailed("Invalid embedding count")
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS:
            raise EmbeddingFailed("Invalid embedding dimensions")
        if any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or abs(v) > 3.4e38
            for v in vector
        ):
            raise EmbeddingFailed("Invalid embedding values")
        if not any(v != 0 for v in vector):
            raise EmbeddingFailed("Zero embedding vector")
    return vectors


class OpenAIEmbeddingModel:
    def __init__(self, *, api_key: str, base_url: str, model: str, timeout: float, transport=None):
        self.api_key, self.base_url, self.model = api_key, base_url, model
        self.timeout, self.transport = timeout, transport

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key or not self.base_url or not self.model:
            raise UnconfiguredError("Embedding provider is not configured")
        if not texts:
            return []
        # Bounds match our chunker and avoid exceeding provider token limits even for UTF-8.
        if len(texts) > 16 or any(not t.strip() or len(t) > 1200 for t in texts):
            raise EmbeddingFailed("Embedding input exceeds the supported batch bounds")
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(
                    self.base_url.rstrip("/") + "/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "input": texts,
                        "dimensions": EMBEDDING_DIMENSIONS,
                        "encoding_format": "float",
                    },
                )
                response.raise_for_status()
                data = response.json()
            if data.get("model") != self.model:
                raise EmbeddingFailed("Embedding response model does not match configuration")
            rows = data["data"]
            indexes = [row["index"] for row in rows]
            if any(type(index) is not int for index in indexes) or sorted(indexes) != list(
                range(len(texts))
            ):
                raise EmbeddingFailed("Invalid embedding response indexes")
            return validate_vectors(
                [row["embedding"] for row in sorted(rows, key=lambda r: r["index"])], len(texts)
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            # Never include provider response bodies, input text, or credential-bearing URLs.
            raise EmbeddingFailed("Embedding provider request failed") from exc
