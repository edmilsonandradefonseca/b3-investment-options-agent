from __future__ import annotations

from dataclasses import dataclass
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
    """Contract for embedding providers; implementation is intentionally deferred."""

    @property
    def model(self) -> str: ...

    def embed(self, texts: Sequence[str]) -> tuple[Embedding, ...]: ...


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
