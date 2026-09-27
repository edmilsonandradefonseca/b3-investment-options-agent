from __future__ import annotations

from dataclasses import dataclass

from .embeddings import EmbeddingProvider
from .obsidian import ObsidianKnowledgeStore
from .qdrant_store import QdrantVectorStore


@dataclass(frozen=True)
class RetrievedEvidence:
    """A bounded piece of retrieved investor evidence."""

    source_ref: str
    relative_path: str
    snippet: str
    score: float


class VectorEvidenceRetriever:
    """V4 production retriever over the B3-owned Qdrant hybrid collection."""

    def __init__(self, store: QdrantVectorStore, embeddings: EmbeddingProvider) -> None:
        self.store = store
        self.embeddings = embeddings

    def retrieve(self, query: str, *, top_k: int = 5) -> tuple[RetrievedEvidence, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        embedding = self.embeddings.embed((query.strip(),))[0]
        if self.store.hybrid:
            results = self.store.hybrid_search(
                query.strip(), embedding, top_k=top_k, prefetch_k=max(top_k * 4, top_k)
            )
        else:
            results = self.store.search(embedding, top_k=top_k)

        return tuple(
            RetrievedEvidence(
                source_ref=str(item.metadata.get("source") or item.evidence_id),
                relative_path=str(item.metadata.get("document_id") or item.metadata.get("canonical_id") or item.chunk_id),
                snippet=item.content[:800],
                score=float(item.score),
            )
            for item in results
        )


class ObsidianRetriever:
    """Legacy deterministic retriever retained only for compatibility/tests."""

    def __init__(self, store: ObsidianKnowledgeStore):
        self.store = store

    def retrieve(self, query: str, *, top_k: int = 5) -> tuple[RetrievedEvidence, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        terms = tuple(dict.fromkeys(query.casefold().split()))
        scored: list[RetrievedEvidence] = []

        for relative_path in self.store.list_notes():
            content = self.store.read_note(relative_path)
            normalized = content.casefold()
            score = sum(normalized.count(term) for term in terms)
            if score == 0:
                continue

            snippet = _bounded_snippet(content, terms)
            scored.append(
                RetrievedEvidence(
                    source_ref=f"obsidian:{relative_path.as_posix()}",
                    relative_path=relative_path.as_posix(),
                    snippet=snippet,
                    score=float(score),
                )
            )

        scored.sort(key=lambda item: (-item.score, item.relative_path))
        return tuple(scored[:top_k])


def _bounded_snippet(content: str, terms: tuple[str, ...], limit: int = 800) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if any(term in line.casefold() for term in terms):
            start = max(0, index - 2)
            end = min(len(lines), index + 4)
            snippet = "\n".join(lines[start:end]).strip()
            return snippet[:limit]
    return content.strip()[:limit]
