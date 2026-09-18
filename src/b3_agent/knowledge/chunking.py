from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import re

from .evidence import Evidence, EvidenceMetadata


@dataclass(frozen=True)
class EvidenceChunk:
    """A deterministic RAG chunk that preserves its source metadata."""

    chunk_id: str
    evidence_id: str
    chunk_index: int
    chunk_count: int
    content: str
    metadata: EvidenceMetadata


class EvidenceChunker:
    """Split evidence into bounded, paragraph-aware chunks.

    Chunking is deterministic and deliberately independent of embeddings or an
    LLM. Metadata is copied to every chunk and chunk identity is derived from
    the source evidence id, position, and normalized chunk content.
    """

    def __init__(self, *, max_chars: int = 1200):
        if max_chars < 1:
            raise ValueError("max_chars must be positive")
        self.max_chars = max_chars

    def chunk(self, evidence: Evidence) -> tuple[EvidenceChunk, ...]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", evidence.content) if p.strip()]
        if not paragraphs:
            raise ValueError("evidence content must contain non-empty text")

        pieces: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if len(paragraph) <= self.max_chars:
                candidate = paragraph if not current else f"{current}\n\n{paragraph}"
                if len(candidate) <= self.max_chars:
                    current = candidate
                    continue
                if current:
                    pieces.append(current)
                current = paragraph
                continue

            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_long_text(paragraph, self.max_chars))

        if current:
            pieces.append(current)

        count = len(pieces)
        chunks: list[EvidenceChunk] = []
        for index, content in enumerate(pieces):
            chunk_hash = sha256(content.encode("utf-8")).hexdigest()
            chunk_id = f"{evidence.evidence_id}:{index}:{chunk_hash[:16]}"
            metadata = replace(
                evidence.metadata,
                extra={
                    **evidence.metadata.extra,
                    "chunk_index": index,
                    "chunk_count": count,
                    "parent_evidence_id": evidence.evidence_id,
                    "chunk_content_hash": chunk_hash,
                },
            )
            chunks.append(
                EvidenceChunk(
                    chunk_id=chunk_id,
                    evidence_id=evidence.evidence_id,
                    chunk_index=index,
                    chunk_count=count,
                    content=content,
                    metadata=metadata,
                )
            )
        return tuple(chunks)


def _split_long_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
        if len(word) > max_chars:
            pieces.extend(word[i : i + max_chars] for i in range(0, len(word), max_chars))
            current = ""
        else:
            current = word
    if current:
        pieces.append(current)
    return pieces
