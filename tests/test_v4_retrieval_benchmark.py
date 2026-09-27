import pytest

from b3_agent.knowledge.retrieval_benchmark import RetrievalBenchmark, RetrievalBenchmarkCase
from b3_agent.knowledge.vector_store import VectorSearchResult


def result(evidence_id):
    return VectorSearchResult(
        chunk_id=f"CH-{evidence_id}", evidence_id=evidence_id,
        score=1.0, content=f"content {evidence_id}",
    )


def test_benchmark_computes_precision_recall_mrr_ndcg():
    cases = (
        RetrievalBenchmarkCase("Q1", "petr4", ("A", "B"), top_k=2),
        RetrievalBenchmarkCase("Q2", "vale3", ("C",), top_k=2),
    )
    answers = {"Q1": (result("A"), result("X")), "Q2": (result("X"), result("C"))}
    metrics = RetrievalBenchmark().evaluate(cases, lambda case: answers[case.query_id])
    assert metrics.precision_at_k == pytest.approx(0.5)
    assert metrics.recall_at_k == pytest.approx(0.75)
    assert metrics.mrr == pytest.approx(0.75)
    assert 0.0 < metrics.ndcg_at_k < 1.0
    assert metrics.case_count == 2
    assert metrics.mean_latency_ms >= 0.0


def test_benchmark_compares_profiles_without_declaring_a_winner():
    case = RetrievalBenchmarkCase("Q", "exact ticker option", ("TARGET",), top_k=2)
    profiles = {
        "dense": lambda _: (result("OTHER"), result("TARGET")),
        "dense_sparse_rrf": lambda _: (result("TARGET"), result("OTHER")),
    }
    comparison = RetrievalBenchmark().compare((case,), profiles)
    assert set(comparison) == {"dense", "dense_sparse_rrf"}
    assert comparison["dense_sparse_rrf"].mrr > comparison["dense"].mrr
