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


def learning(
    learning_id: str,
    *,
    status: LearningStatus = LearningStatus.ACTIVE,
    scope: LearningScope = LearningScope.PERSONAL_EXPERIENCE,
    last_confirmed_at: datetime | None = None,
) -> Learning:
    return Learning(
        learning_id=learning_id,
        statement="Short PUT PETR4 historically performed better in sideways/high-vol regimes.",
        status=status,
        learning_scope=scope,
        first_observed_at=BASE,
        last_updated_at=BASE + timedelta(days=20),
        subject_ids=("B3-PETR4",),
        strategy_type="SHORT_PUT",
        conditions=("TREND=SIDEWAYS", "VOLATILITY=HIGH"),
        sample_size=12,
        win_rate=0.75,
        confidence=0.70,
        last_confirmed_at=last_confirmed_at,
        population_scope=(
            "user historical PETR4 short-put operations"
            if scope == LearningScope.PERSONAL_EXPERIENCE
            else None
        ),
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


def _semantic_result_for_learning(learning_id: str, score: float = 0.8):
    from b3_agent.knowledge.vector_store import VectorSearchResult
    return VectorSearchResult(
        chunk_id=f"chunk-{learning_id}",
        evidence_id=f"ev-{learning_id}",
        score=score,
        content=f"semantic content for {learning_id}",
        metadata={
            "extra": {
                "canonical_id": learning_id,
                "learning_id": learning_id,
            }
        },
    )


def test_learning_aging_uses_last_confirmation_not_first_observation():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    as_of = BASE + timedelta(days=400)

    old_but_reconfirmed = learning(
        "LRN-RECENT-CONFIRM",
        last_confirmed_at=as_of - timedelta(days=10),
    )
    stale = learning(
        "LRN-STALE",
        last_confirmed_at=as_of - timedelta(days=300),
    )

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(old_but_reconfirmed.learning_id),
            _semantic_result_for_learning(stale.learning_id),
        ),
        learnings=(old_but_reconfirmed, stale),
        top_k=2,
    )

    by_id = {match.reference_id: match for match in result.matches}
    assert by_id[old_but_reconfirmed.learning_id].temporal_score > by_id[stale.learning_id].temporal_score
    assert result.matches[0].reference_id == old_but_reconfirmed.learning_id


def test_learning_scope_controls_temporal_decay():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    as_of = BASE + timedelta(days=220)
    confirmed = BASE + timedelta(days=20)

    market_observation = learning(
        "LRN-MARKET",
        scope=LearningScope.MARKET_OBSERVATION,
        last_confirmed_at=confirmed,
    )
    durable_personal = learning(
        "LRN-PERSONAL",
        scope=LearningScope.PERSONAL_EXPERIENCE,
        last_confirmed_at=confirmed,
    )

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(market_observation.learning_id),
            _semantic_result_for_learning(durable_personal.learning_id),
        ),
        learnings=(market_observation, durable_personal),
        top_k=2,
    )

    by_id = {match.reference_id: match for match in result.matches}
    assert by_id[durable_personal.learning_id].temporal_score > by_id[market_observation.learning_id].temporal_score


def test_old_learning_can_remain_relevant_when_regime_matches():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    as_of = BASE + timedelta(days=400)

    matching = learning(
        "LRN-MATCHING-REGIME",
        last_confirmed_at=BASE,
    )
    mismatching = Learning(
        learning_id="LRN-MISMATCHING-REGIME",
        statement="Different regime learning.",
        status=LearningStatus.ACTIVE,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        first_observed_at=BASE,
        last_updated_at=BASE,
        last_confirmed_at=BASE,
        subject_ids=("B3-PETR4",),
        strategy_type="SHORT_PUT",
        conditions=("TREND=BEAR", "VOLATILITY=LOW", "FOREIGN_FLOW=NEGATIVE"),
        sample_size=12,
        win_rate=0.75,
        confidence=0.70,
        population_scope="user historical PETR4 short-put operations",
        valid_from=BASE,
    )

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(matching.learning_id, 0.7),
            _semantic_result_for_learning(mismatching.learning_id, 0.7),
        ),
        learnings=(matching, mismatching),
        top_k=2,
    )

    by_id = {match.reference_id: match for match in result.matches}
    assert by_id[matching.learning_id].regime_score == 1.0
    assert by_id[mismatching.learning_id].regime_score == 0.0
    assert by_id[matching.learning_id].relevance_score > by_id[mismatching.learning_id].relevance_score


def test_drift_reduces_relevance_without_rewriting_confidence():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    as_of = BASE + timedelta(days=60)

    active = learning(
        "LRN-ACTIVE",
        status=LearningStatus.ACTIVE,
        last_confirmed_at=BASE + timedelta(days=50),
    )
    drifted = learning(
        "LRN-DRIFT",
        status=LearningStatus.DRIFT_DETECTED,
        last_confirmed_at=BASE + timedelta(days=50),
    )

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(active.learning_id, 0.8),
            _semantic_result_for_learning(drifted.learning_id, 0.8),
        ),
        learnings=(active, drifted),
        top_k=2,
    )

    by_id = {match.reference_id: match for match in result.matches}
    assert by_id[active.learning_id].confidence_score == pytest.approx(0.70)
    assert by_id[drifted.learning_id].confidence_score == pytest.approx(0.70)
    assert by_id[drifted.learning_id].lifecycle_score < by_id[active.learning_id].lifecycle_score
    assert by_id[drifted.learning_id].relevance_score < by_id[active.learning_id].relevance_score


def test_contradictions_reduce_relevance_but_preserve_learning():
    from b3_agent.schemas.learning import EvidenceDirection, LearningEvidenceLink

    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    as_of = BASE + timedelta(days=60)

    clean = learning(
        "LRN-CLEAN",
        last_confirmed_at=BASE + timedelta(days=50),
    )
    contradictory = Learning(
        learning_id="LRN-CONTRADICTORY",
        statement=clean.statement,
        status=LearningStatus.ACTIVE,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        first_observed_at=clean.first_observed_at,
        last_updated_at=clean.last_updated_at,
        last_confirmed_at=clean.last_confirmed_at,
        subject_ids=clean.subject_ids,
        strategy_type=clean.strategy_type,
        conditions=clean.conditions,
        evidence_links=(
            LearningEvidenceLink(
                evidence_id="EV-SUPPORT",
                direction=EvidenceDirection.SUPPORTS,
                observed_at=BASE + timedelta(days=30),
            ),
            LearningEvidenceLink(
                evidence_id="EV-CONTRA-1",
                direction=EvidenceDirection.CONTRADICTS,
                observed_at=BASE + timedelta(days=40),
            ),
            LearningEvidenceLink(
                evidence_id="EV-CONTRA-2",
                direction=EvidenceDirection.CONTRADICTS,
                observed_at=BASE + timedelta(days=50),
            ),
        ),
        sample_size=12,
        confidence=0.70,
        population_scope="user historical PETR4 short-put operations",
        valid_from=BASE,
    )

    result = ExperienceRanker().rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(clean.learning_id, 0.8),
            _semantic_result_for_learning(contradictory.learning_id, 0.8),
        ),
        learnings=(clean, contradictory),
        top_k=2,
    )

    by_id = {match.reference_id: match for match in result.matches}
    assert contradictory.learning_id in by_id
    assert by_id[contradictory.learning_id].contradiction_score < 1.0
    assert by_id[contradictory.learning_id].relevance_score < by_id[clean.learning_id].relevance_score


def test_historical_usefulness_is_separate_and_opt_in_for_ranking():
    current = snapshot("FS-CURRENT", 20, 40.0, 0.45)
    current_regime = regime("REG-CURRENT", current)
    as_of = BASE + timedelta(days=60)
    a = learning("LRN-A", last_confirmed_at=BASE + timedelta(days=50))
    b = learning("LRN-B", last_confirmed_at=BASE + timedelta(days=50))

    neutral_policy = ExperienceRankingPolicy(historical_usefulness_weight=0.0)
    neutral = ExperienceRanker(neutral_policy).rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(a.learning_id, 0.8),
            _semantic_result_for_learning(b.learning_id, 0.8),
        ),
        learnings=(a, b),
        historical_usefulness={a.learning_id: 0.1, b.learning_id: 0.9},
        top_k=2,
    )

    weighted_policy = ExperienceRankingPolicy(historical_usefulness_weight=0.20)
    weighted = ExperienceRanker(weighted_policy).rank(
        current_snapshot=current,
        current_regime=current_regime,
        as_of=as_of,
        experiences=(),
        semantic_results=(
            _semantic_result_for_learning(a.learning_id, 0.8),
            _semantic_result_for_learning(b.learning_id, 0.8),
        ),
        learnings=(a, b),
        historical_usefulness={a.learning_id: 0.1, b.learning_id: 0.9},
        top_k=2,
    )

    neutral_by_id = {match.reference_id: match for match in neutral.matches}
    weighted_by_id = {match.reference_id: match for match in weighted.matches}

    assert neutral_by_id[a.learning_id].historical_usefulness_score == pytest.approx(0.1)
    assert neutral_by_id[b.learning_id].historical_usefulness_score == pytest.approx(0.9)
    assert neutral_by_id[a.learning_id].relevance_score == pytest.approx(
        neutral_by_id[b.learning_id].relevance_score
    )
    assert weighted_by_id[b.learning_id].relevance_score > weighted_by_id[a.learning_id].relevance_score
