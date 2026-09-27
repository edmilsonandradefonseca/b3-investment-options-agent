from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.request
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Embedding:
    """A provider-neutral vector representation of one text input."""

    values: tuple[float, ...]
    model: str

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("embedding values must not be empty")
        if not self.model.strip():
            raise ValueError("embedding model must not be empty")
        if not all(isinstance(value, (int, float)) for value in self.values):
            raise ValueError("embedding values must be numeric")


class EmbeddingProvider(Protocol):
    """Provider-neutral embedding boundary."""

    @property
    def model(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> tuple[Embedding, ...]: ...


class HttpEmbeddingProvider:
    """Production adapter for the shared local embedding HTTP service."""

    def __init__(self, *, base_url: str, dimensions: int = 768, model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", timeout: float = 30.0) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self.base_url = base_url.rstrip("/")
        self.dimensions = dimensions
        self._model = model
        self.timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: Sequence[str]) -> tuple[Embedding, ...]:
        result: list[Embedding] = []
        for text in texts:
            if not text.strip():
                raise ValueError("text must not be empty")
            request = urllib.request.Request(
                f"{self.base_url}/embed",
                data=json.dumps({"text": text}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            values = tuple(float(value) for value in payload.get("embedding", ()))
            dimensions = int(payload.get("dimensions") or len(values))
            if dimensions != self.dimensions or len(values) != self.dimensions:
                raise ValueError(f"embedding service returned {len(values)} dimensions; expected {self.dimensions}")
            result.append(Embedding(values=values, model=str(payload.get("model") or self._model)))
        return tuple(result)


class DeterministicEmbeddingProvider:
    """Small test provider; not intended for semantic production retrieval."""

    def __init__(self, *, dimensions: int = 8, model: str = "deterministic-test-v1"):
        if dimensions < 1:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    def embed(self, texts: Sequence[str]) -> tuple[Embedding, ...]:
        import hashlib
        result: list[Embedding] = []
        for text in texts:
            if not text.strip():
                raise ValueError("text must not be empty")
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = tuple((digest[i % len(digest)] / 255.0) for i in range(self._dimensions))
            result.append(Embedding(values=values, model=self._model))
        return tuple(result)
