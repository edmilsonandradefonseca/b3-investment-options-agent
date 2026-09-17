import pytest

from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider


def test_embedding_provider_is_deterministic() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=4)
    first = provider.embed(["PETR4 market evidence"])
    second = provider.embed(["PETR4 market evidence"])

    assert first == second
    assert len(first) == 1
    assert len(first[0].values) == 4
    assert first[0].model == "deterministic-test-v1"


def test_embedding_provider_preserves_batch_order() -> None:
    provider = DeterministicEmbeddingProvider(dimensions=3)
    embeddings = provider.embed(["alpha", "beta"])

    assert len(embeddings) == 2
    assert embeddings[0] != embeddings[1]


def test_empty_text_is_rejected() -> None:
    provider = DeterministicEmbeddingProvider()
    with pytest.raises(ValueError):
        provider.embed([" "])
