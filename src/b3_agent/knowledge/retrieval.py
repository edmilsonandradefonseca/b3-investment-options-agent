from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .obsidian import ObsidianKnowledgeStore


@dataclass(frozen=True)
class RetrievedEvidence:
    """A bounded piece of investor knowledge retrieved from Obsidian."""

    source_ref: str
    relative_path: str
    snippet: str
    score: int


class ObsidianRetriever:
    """Deterministic local retriever over the investor's Obsidian vault.

    This is the MVP retrieval contract. It deliberately keeps retrieval
    provider-independent so semantic/vector retrieval can replace the ranking
    implementation without changing the graph or agents.
    """

    def __init__(self, store: ObsidianKnowledgeStore):
        self.store = store

    def retrieve(self, query: str, *, top_k: int = 5) -> tuple[RetrievedEvidence, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1:
            raise ValueError("top_k must be positive")

        terms = tuple(dict.fromkeys(_query_terms(query)))
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
                    score=score,
                )
            )

        scored.sort(key=lambda item: (-item.score, item.relative_path))
        return tuple(scored[:top_k])


def _query_terms(query: str) -> tuple[str, ...]:
    """Tokenize queries independently of punctuation and case.

    Natural-language dashboard questions commonly contain punctuation such as
    ``oportunidade?`` or currency notation such as ``R$``. Splitting only on
    whitespace makes those tokens impossible to match against clean note text.
    """
    return tuple(
        term
        for term in dict.fromkeys(re.findall(r"\w+", query.casefold()))
        if len(term) > 1
    )

def _bounded_snippet(content: str, terms: tuple[str, ...], limit: int = 800) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if any(term in line.casefold() for term in terms):
            start = max(0, index - 2)
            end = min(len(lines), index + 4)
            snippet = "\n".join(lines[start:end]).strip()
            return snippet[:limit]
    return content.strip()[:limit]
