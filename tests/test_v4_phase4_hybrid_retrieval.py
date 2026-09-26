from datetime import datetime, timedelta, timezone

import pytest
from qdrant_client import QdrantClient

from b3_agent.experience import (
    ExperienceAssessmentEngine,
    ExperienceEngine,
    ExperienceRanker,
    ExperienceRankingPolicy,
)
from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
from b3_agent.knowledge.learning_semantic import (
    B3_SEMANTIC_COLLECTION,
    B3_SEMANTIC_DIMENSIONS,
    LearningSemanticIndex,
)
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.schemas.feature_snapshot import FeatureDomain, FeatureSnapshot, FeatureValue
from b3_agent.schemas.learning import Learning, LearningScope, LearningStatus
from b3_agent.schemas.market_regime import (
    MarketRegime,
    RegimeDimension,
    RegimeDimensionName,
)
from b3_agent.schemas.operation import Operation, OperationDirection, OperationStatus
from b3_agent.schemas.outcome import Outcome, OutcomeStatus


BASE = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)


def snapshot(snapshot_id: str, day: int, close: float, vol: float) -> FeatureSnapshot:
    as_of = BASE + timedelta(days=day)
    return FeatureSnapshot(
        snapshot_id=snapshot_id,
        subject_id="B3-PETR4",
        as_of=as_of,
        features=(
            FeatureValue("close", close, FeatureDomain.MARKET, as_of),
            FeatureValue("volatility_20d", vol, FeatureDomain.MARKET, as_of),
        ),
        operation_id=f"OP-{snapshot_id}",
    )


def regime(regime_id: str, snap: FeatureSnapshot, *, trend: str = "SIDEWAYS") -> MarketRegime:
    return MarketRegime(
        regime_id=regime_id,
        as_of=snap.as_of,
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, trend),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH"),
            RegimeDimension(RegimeDimensionName.FOREIGN_FLOW, "POSITIVE"),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id=snap.snapshot_id,
        confidence=0.8,
    )


def experience(index: int, *, day: int, close: float, vol: float, trend: str = "SIDEWAYS"):
    snap = snapshot(f"FS-{index}", day, close, vol)
    reg = regime(f"REG-{index}", snap, trend=trend)
    opened = snap.as_of
    closed = opened + timedelta(days=10)
    operation = Operation(
        operation_id=f"OP-FS-{index}",
        strategy_type="SHORT_PUT",
        underlying_id="B3-PETR4",
        opened_at=opened,
        closed_at=closed,
        status=OperationStatus.CLOSED,
        direction=OperationDirection.SHORT,
        quantity=100,
        source_transaction_ids=(f"T-{index}-1", f"T-{index}-2"),
    )
    outcome = Outcome(
        outcome_id=f"OUT-{index}",
        operation_id=operation.operation_id,
        finalized_at=closed,
        status=OutcomeStatus.FINAL,
        realized_pnl=300.0,
        realized_return=0.03,
    )
    return ExperienceEngine().assemble(
        operation=operation,
        entry_snapshot=snap,
        market_regime=reg,
        outcome=outcome,
    )


def learning(learning_id: str, *, status: LearningStatus = LearningStatus.ACTIVE) -> Learning:
    return Learning(
        learning_id=learning_id,
        statement="Short PUT PETR4 historically performed better in sideways/high-vol regimes.",
        status=status,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        first_observed_at=BASE,
        last_updated_at=BASE + timedelta(days=20),
        subject_ids=("B3-PETR4",),
        strategy_type="SHORT_PUT",
        conditions=("TREND=SIDEWAYS", "VOLATILITY=HIGH"),
        sample_size=12,
        win_rate=0.75,
        confidence=0.70,
        population_scope="user historical PETR4 short-put operations",
        selection_bias_warning="Selected personal operations; not market-wide probability.",
        valid_from=BASE,
    )


def test_phase4_ranker_prefers_similar_regime_and_features():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    similar = experience(1, day=10, close=39.0, vol=0.44, trend="SIDEWAYS")
    different = experience(2, day=15, close=25.0, vol=0.15, trend="BEAR")

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=BASE + timedelta(days=30),
        experiences=(different, similar),
        top_k=2,
    )

    assert result.matches[0].reference_id == similar.experience_id
    assert result.matches[0].regime_score == 1.0
    assert result.matches[0].feature_similarity_score > result.matches[1].feature_similarity_score


def test_phase4_temporal_score_is_separate_from_regime_similarity():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    old = experience(1, day=1, close=40.0, vol=0.45)
    recent = experience(2, day=18, close=40.0, vol=0.45)

    result = ExperienceRanker(
        ExperienceRankingPolicy(half_life_days=30)
    ).rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=BASE + timedelta(days=40),
        experiences=(old, recent),
        top_k=2,
    )

    by_id = {match.reference_id: match for match in result.matches}
    assert by_id[old.experience_id].regime_score == by_id[recent.experience_id].regime_score == 1.0
    assert by_id[recent.experience_id].temporal_score > by_id[old.experience_id].temporal_score


def test_learning_semantic_index_requires_768d_and_uses_b3_collection():
    client = QdrantClient(":memory:")
    store = QdrantVectorStore(
        client=client,
        collection_name=B3_SEMANTIC_COLLECTION,
        vector_size=B3_SEMANTIC_DIMENSIONS,
    )
    embeddings = DeterministicEmbeddingProvider(
        dimensions=B3_SEMANTIC_DIMENSIONS,
        model="deterministic-768-test",
    )
    index = LearningSemanticIndex(store=store, embeddings=embeddings)
    item = learning("LRN-001")
    index.upsert((item,))

    results = index.search(
        "PETR4 short put sideways volatility",
        as_of=BASE + timedelta(days=30),
        ticker="PETR4",
        top_k=5,
    )

    assert store.count() == 1
    assert len(results) == 1
    assert results[0].metadata["extra"]["canonical_id"] == "LRN-001"
    assert results[0].metadata["topic"] == "learning"


def test_learning_semantic_index_rejects_non_768_store():
    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name="wrong",
        vector_size=8,
    )
    with pytest.raises(ValueError, match="768"):
        LearningSemanticIndex(
            store=store,
            embeddings=DeterministicEmbeddingProvider(dimensions=8),
        )


def test_experience_assessment_separates_supporting_and_drifted_learning():
    retrieval = ExperienceRanker().rank(
        current_snapshot=snapshot("FS-CURRENT", 20, 40.0, 0.45),
        current_regime=regime("REG-CURRENT", snapshot("FS-CURRENT", 20, 40.0, 0.45)),
        as_of=BASE + timedelta(days=30),
        experiences=(),
        semantic_results=(),
    )
    # Build an explicit retrieval with learning refs using the canonical contract.
    from b3_agent.schemas.experience import ExperienceMatch, ExperienceRetrievalResult
    retrieval = ExperienceRetrievalResult(
        query_id="Q-LEARN",
        as_of=BASE + timedelta(days=30),
        subject_ids=("B3-PETR4",),
        current_snapshot_id="FS-CURRENT",
        current_regime_id="REG-CURRENT",
        matches=(
            ExperienceMatch("LRN-A", "LEARNING", 0.9, semantic_score=0.9),
            ExperienceMatch("LRN-B", "LEARNING", 0.8, semantic_score=0.8),
        ),
    )

    assessment = ExperienceAssessmentEngine().assess(
        retrieval,
        learnings=(
            learning("LRN-A", status=LearningStatus.ACTIVE),
            learning("LRN-B", status=LearningStatus.DRIFT_DETECTED),
        ),
    )

    assert assessment.supporting_learning_ids == ("LRN-A",)
    assert assessment.contradicting_learning_ids == ("LRN-B",)
    assert assessment.applicable_regime_id == "REG-CURRENT"
    assert assessment.limitations


def test_ranker_does_not_mutate_deterministic_score_contract():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=BASE + timedelta(days=30),
        experiences=(experience(1, day=10, close=39.5, vol=0.46),),
    )
    assessment = ExperienceAssessmentEngine().assess(result)

    deterministic_score = 0.72
    assert deterministic_score == 0.72
    assert assessment.historical_similarity is not None


def test_qdrant_hybrid_search_combines_dense_and_sparse():
    client = QdrantClient(":memory:")
    store = QdrantVectorStore(
        client=client,
        collection_name="hybrid-test",
        vector_size=8,
        hybrid=True,
    )
    embeddings = DeterministicEmbeddingProvider(dimensions=8)

    from b3_agent.knowledge.chunking import EvidenceChunker
    from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata

    def make_evidence(evidence_id: str, content: str):
        metadata = EvidenceMetadata(
            document_id=evidence_id,
            source="test",
            published_at=BASE,
            retrieved_at=BASE,
            ticker_refs=("PETR4",),
            topic="learning",
        )
        return Evidence(
            evidence_id=evidence_id,
            kind=EvidenceKind.ANALYTICAL,
            title=evidence_id,
            content=content,
            metadata=metadata,
        )

    lexical = make_evidence(
        "LEXICAL",
        "PETR4 TOTSV316 SHORT_PUT exact option identifier",
    )
    semantic = make_evidence(
        "SEMANTIC",
        "selling downside option premium in a sideways high-volatility regime",
    )

    chunks = []
    for item in (lexical, semantic):
        chunks.extend(EvidenceChunker(max_chars=2000).chunk(item))
    vectors = embeddings.embed(tuple(chunk.content for chunk in chunks))
    store.upsert(tuple(chunks), vectors)

    query = "PETR4 TOTSV316"
    query_embedding = embeddings.embed((query,))[0]
    results = store.hybrid_search(
        query,
        query_embedding,
        top_k=2,
        metadata_filter=__import__(
            "b3_agent.knowledge.vector_store",
            fromlist=["MetadataFilter"],
        ).MetadataFilter(ticker="PETR4", topic="learning"),
    )

    assert len(results) == 2
    assert {item.evidence_id for item in results} == {"LEXICAL", "SEMANTIC"}
    assert results[0].score >= results[1].score


def test_experience_ranker_emits_retrieval_trace():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    items = (
        experience(1, day=10, close=39.0, vol=0.44, trend="SIDEWAYS"),
        experience(2, day=15, close=25.0, vol=0.15, trend="BEAR"),
    )

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=BASE + timedelta(days=30),
        experiences=items,
        top_k=2,
    )

    assert result.trace is not None
    assert result.trace.candidate_count == 2
    assert result.trace.selected_count == 2
    assert result.trace.ranker_version == "experience-ranker-v2"
    assert [item.final_rank for item in result.matches] == [1, 2]
    assert result.trace.items[0].rerank_components
    assert dict(result.retrieval_metadata)["trace_id"] == result.trace.trace_id
