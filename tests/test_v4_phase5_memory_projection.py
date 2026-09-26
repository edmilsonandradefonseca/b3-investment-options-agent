from datetime import datetime, timedelta, timezone

from qdrant_client import QdrantClient

from b3_agent.knowledge.embeddings import DeterministicEmbeddingProvider
from b3_agent.knowledge.graph_schema import EntityType, RelationType
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.learning_semantic import (
    B3_SEMANTIC_COLLECTION,
    B3_SEMANTIC_DIMENSIONS,
    LearningSemanticIndex,
)
from b3_agent.knowledge.projection import MemoryProjectionBridge, SQLiteProjectionLedger
from b3_agent.knowledge.qdrant_store import QdrantVectorStore
from b3_agent.schemas.learning import (
    EvidenceDirection,
    Learning,
    LearningEvidenceLink,
    LearningScope,
    LearningStatus,
)
from b3_agent.schemas.market_regime import MarketRegime, RegimeDimension, RegimeDimensionName
from b3_agent.schemas.operation import Operation, OperationDirection, OperationStatus
from b3_agent.schemas.outcome import Outcome, OutcomeStatus


BASE = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)


def make_operation():
    return Operation(
        operation_id="OP-001",
        strategy_type="SHORT_PUT",
        underlying_id="B3-PETR4",
        opened_at=BASE,
        closed_at=BASE + timedelta(days=10),
        status=OperationStatus.CLOSED,
        direction=OperationDirection.SHORT,
        quantity=100,
        capital_committed=3500.0,
        source_transaction_ids=("TX-1", "TX-2"),
        provenance="test",
    )


def make_outcome():
    return Outcome(
        outcome_id="OUT-001",
        operation_id="OP-001",
        finalized_at=BASE + timedelta(days=10),
        status=OutcomeStatus.FINAL,
        realized_pnl=300.0,
        realized_return=0.0857,
        holding_period_days=10,
        provenance="test",
    )


def make_regime():
    return MarketRegime(
        regime_id="REG-001",
        as_of=BASE,
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, "SIDEWAYS"),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH"),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id="FS-001",
        confidence=0.8,
        valid_from=BASE,
        provenance="test",
    )


def make_learning():
    return Learning(
        learning_id="LRN-001",
        statement="Observed favorable personal outcomes for PETR4 short puts in sideways/high-vol regimes.",
        status=LearningStatus.ACTIVE,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        first_observed_at=BASE,
        last_updated_at=BASE + timedelta(days=20),
        subject_ids=("B3-PETR4",),
        strategy_type="SHORT_PUT",
        conditions=("TREND=SIDEWAYS", "VOLATILITY=HIGH"),
        regime_ids=("REG-001",),
        evidence_links=(
            LearningEvidenceLink(
                evidence_id="EV-1",
                direction=EvidenceDirection.SUPPORTS,
                operation_id="OP-001",
                source_ref="EXP-001",
                observed_at=BASE + timedelta(days=10),
            ),
        ),
        sample_size=10,
        win_rate=0.8,
        confidence=0.7,
        population_scope="user PETR4 short-put operations",
        selection_bias_warning="Selected personal operations.",
        statistical_method="descriptive-personal-cohort-v1",
        model_version="learning-engine-v1",
        valid_from=BASE,
        provenance="test",
    )


def test_projection_bridge_projects_operation_outcome_and_regime(tmp_path):
    graph = InMemoryKnowledgeGraphStore()
    ledger = SQLiteProjectionLedger(tmp_path / "projection.db")
    bridge = MemoryProjectionBridge(graph=graph, ledger=ledger)

    bridge.project_operation(
        operation=make_operation(),
        outcome=make_outcome(),
        regime=make_regime(),
    )

    assert graph.get_entity("OP-001").entity_type == EntityType.OPERATION
    assert graph.get_entity("OUT-001").entity_type == EntityType.OUTCOME
    assert graph.get_entity("REG-001").entity_type == EntityType.MARKET_REGIME
    assert graph.count_relations(relation=RelationType.HAS_OUTCOME) == 1
    assert graph.count_relations(relation=RelationType.OCCURRED_IN) == 1
    assert graph.count_relations(relation=RelationType.USES) == 1

    statuses = ledger.get("OP-001", "1.0")
    assert len(statuses) == 1
    assert statuses[0].target == "neo4j"
    assert statuses[0].status == "OK"


def test_projection_bridge_projects_learning_to_graph_and_qdrant(tmp_path):
    graph = InMemoryKnowledgeGraphStore()
    ledger = SQLiteProjectionLedger(tmp_path / "projection.db")
    store = QdrantVectorStore(
        client=QdrantClient(":memory:"),
        collection_name=B3_SEMANTIC_COLLECTION,
        vector_size=B3_SEMANTIC_DIMENSIONS,
    )
    semantic = LearningSemanticIndex(
        store=store,
        embeddings=DeterministicEmbeddingProvider(
            dimensions=B3_SEMANTIC_DIMENSIONS,
            model="deterministic-768-test",
        ),
    )
    bridge = MemoryProjectionBridge(
        graph=graph,
        ledger=ledger,
        semantic=semantic,
    )

    bridge.project_learning(make_learning())

    assert graph.get_entity("LRN-001").entity_type == EntityType.LEARNING
    assert graph.count_relations(relation=RelationType.ABOUT) == 1
    assert graph.count_relations(relation=RelationType.VALID_IN) == 1
    assert graph.count_relations(relation=RelationType.SUPPORTED_BY) == 1
    assert store.count() == 1

    statuses = {item.target: item.status for item in ledger.get("LRN-001", "1.0")}
    assert statuses == {"neo4j": "OK", "qdrant": "OK"}


def test_projection_is_idempotent_for_same_canonical_version(tmp_path):
    graph = InMemoryKnowledgeGraphStore()
    ledger = SQLiteProjectionLedger(tmp_path / "projection.db")
    bridge = MemoryProjectionBridge(graph=graph, ledger=ledger)

    learning = make_learning()
    bridge.project_learning(learning)
    bridge.project_learning(learning)

    assert graph.count_entities(entity_type=EntityType.LEARNING) == 1
    statuses = ledger.get("LRN-001", "1.0")
    assert len(statuses) == 1
    assert statuses[0].status == "OK"


def test_projection_failure_is_recorded_as_degraded_state(tmp_path):
    class FailingGraph(InMemoryKnowledgeGraphStore):
        def upsert(self, entities, relations):
            raise RuntimeError("neo4j unavailable")

    ledger = SQLiteProjectionLedger(tmp_path / "projection.db")
    bridge = MemoryProjectionBridge(graph=FailingGraph(), ledger=ledger)

    try:
        bridge.project_learning(make_learning())
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected projection failure")

    statuses = ledger.get("LRN-001", "1.0")
    assert statuses[0].target == "neo4j"
    assert statuses[0].status == "FAILED"
    assert "unavailable" in statuses[0].error
