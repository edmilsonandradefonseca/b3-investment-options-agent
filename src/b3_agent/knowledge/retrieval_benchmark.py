from __future__ import annotations

from dataclasses import dataclass
from math import log2
from time import perf_counter
from typing import Callable, Iterable, Mapping, Sequence

from b3_agent.knowledge.vector_store import VectorSearchResult


@dataclass(frozen=True)
class RetrievalBenchmarkCase:
    query_id: str
    query: str
    relevant_ids: tuple[str, ...]
    top_k: int = 5

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.query.strip():
            raise ValueError("query_id and query must be non-empty")
        if not self.relevant_ids:
            raise ValueError("relevant_ids must not be empty")
        if self.top_k < 1:
            raise ValueError("top_k must be positive")


@dataclass(frozen=True)
class RetrievalBenchmarkMetrics:
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    mean_latency_ms: float
    case_count: int


class RetrievalBenchmark:
    """Provider-neutral benchmark for dense, hybrid and reranked retrieval profiles."""

    def evaluate(
        self,
        cases: Iterable[RetrievalBenchmarkCase],
        retriever: Callable[[RetrievalBenchmarkCase], Sequence[VectorSearchResult]],
    ) -> RetrievalBenchmarkMetrics:
        rows = tuple(cases)
        if not rows:
            raise ValueError("benchmark requires at least one case")
        precision = recall = reciprocal_rank = ndcg = latency = 0.0
        for case in rows:
            started = perf_counter()
            results = tuple(retriever(case))[: case.top_k]
            latency += (perf_counter() - started) * 1000.0
            ranked = [item.evidence_id for item in results]
            relevant = set(case.relevant_ids)
            hits = [1 if item in relevant else 0 for item in ranked]
            hit_count = sum(hits)
            precision += hit_count / case.top_k
            recall += hit_count / len(relevant)
            first = next((i for i, value in enumerate(hits, start=1) if value), None)
            reciprocal_rank += 0.0 if first is None else 1.0 / first
            dcg = sum(value / log2(rank + 1) for rank, value in enumerate(hits, start=1))
            ideal_hits = min(len(relevant), case.top_k)
            idcg = sum(1.0 / log2(rank + 1) for rank in range(1, ideal_hits + 1))
            ndcg += 0.0 if idcg == 0 else dcg / idcg
        count = len(rows)
        return RetrievalBenchmarkMetrics(
            precision_at_k=precision / count,
            recall_at_k=recall / count,
            mrr=reciprocal_rank / count,
            ndcg_at_k=ndcg / count,
            mean_latency_ms=latency / count,
            case_count=count,
        )

    def compare(
        self,
        cases: Iterable[RetrievalBenchmarkCase],
        profiles: Mapping[str, Callable[[RetrievalBenchmarkCase], Sequence[VectorSearchResult]]],
    ) -> dict[str, RetrievalBenchmarkMetrics]:
        materialized = tuple(cases)
        return {name: self.evaluate(materialized, retriever) for name, retriever in profiles.items()}
