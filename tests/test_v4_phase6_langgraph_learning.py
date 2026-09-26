from datetime import datetime, timedelta, timezone

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.experience import ExperienceAssessmentEngine, ExperienceEngine, ExperienceRanker
from b3_agent.experience.events import OutcomeFinalized
from b3_agent.knowledge.context import KnowledgeContextBuilder
from b3_agent.knowledge.in_memory_graph import InMemoryKnowledgeGraphStore
from b3_agent.knowledge.projection import MemoryProjectionBridge, SQLiteProjectionLedger
from b3_agent.learning import LearningEngine
from b3_agent.orchestration.experience_workflow import (
    ExperienceContextService,
    PostOutcomeLearningService,
    build_post_outcome_workflow,
)
from b3_agent.orchestration.workflow import build_workflow
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


class FakeLLM:
    def complete_json(self, *, instructions, input_text, schema_name, schema):
        return {
            "action": "NO_CHANGE",
            "subject_id": "PETR4",
            "thesis": "Maintain while evidence remains supportive.",
            "rationale": "Deterministic and historical context do not require a change.",
            "evidence_refs": ["LRN-001"],
            "risks": ["Conditions can change."],
            "opportunity_cost": "Capital remains allocated.",
            "capital_impact": "No immediate change.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Material deterioration."],
        }


def snapshot(operation_id: str = "OP-001"):
    return FeatureSnapshot(
        snapshot_id="FS-001",
        subject_id="B3-PETR4",
        as_of=BASE,
        operation_id=operation_id,
        features=(
            FeatureValue("close", 40.0, FeatureDomain.MARKET, BASE),
            FeatureValue("volatility_20d", 0.45, FeatureDomain.MARKET, BASE),
        ),
    )


def regime(snap=None):
    snap = snap or snapshot()
    return MarketRegime(
        regime_id="REG-001",
        as_of=snap.as_of,
        dimensions=(
            RegimeDimension(RegimeDimensionName.TREND, "SIDEWAYS"),
            RegimeDimension(RegimeDimensionName.VOLATILITY, "HIGH"),
        ),
        classifier_version="regime-v1",
        feature_snapshot_id=snap.snapshot_id,
        confidence=0.8,
    )


def operation():
    return Operation(
        operation_id="OP-001",
        strategy_type="SHORT_PUT",
        underlying_id="B3-PETR4",
        opened_at=BASE,
        closed_at=BASE + timedelta(days=10),
        status=OperationStatus.CLOSED,
        direction=OperationDirection.SHORT,
        quantity=100,
        source_transaction_ids=("TX-1", "TX-2"),
    )


def outcome():
    return Outcome(
        outcome_id="OUT-001",
        operation_id="OP-001",
        finalized_at=BASE + timedelta(days=10),
        status=OutcomeStatus.FINAL,
        realized_pnl=300.0,
        realized_return=0.03,
    )


def historical_experience():
    return ExperienceEngine().assemble(
        operation=operation(),
        entry_snapshot=snapshot(),
        market_regime=regime(),
        outcome=outcome(),
    )


def active_learning():
    return Learning(
        learning_id="LRN-001",
        statement="Observed favorable personal outcomes.",
        status=LearningStatus.ACTIVE,
        learning_scope=LearningScope.PERSONAL_EXPERIENCE,
        first_observed_at=BASE,
        last_updated_at=BASE + timedelta(days=10),
        subject_ids=("B3-PETR4",),
        strategy_type="SHORT_PUT",
        conditions=("TREND=SIDEWAYS", "VOLATILITY=HIGH"),
        sample_size=8,
        win_rate=0.75,
        confidence=0.7,
        population_scope="user PETR4 short-put operations",
        selection_bias_warning="Selected personal operations.",
    )


def test_pre_analysis_experience_is_injected_before_reasoning_without_obsidian():
    exp = historical_experience()
    learning = active_learning()
    service = ExperienceContextService(
        ranker=ExperienceRanker(),
        assessment_engine=ExperienceAssessmentEngine(),
        experience_loader=lambda subject_id, as_of: (exp,),
        learning_loader=lambda subject_id, as_of: (learning,),
    )
    graph = InMemoryKnowledgeGraphStore()
    context_builder = KnowledgeContextBuilder(None, graph)
    workflow = build_workflow(
        reasoning_agent=InvestmentReasoningAgent(FakeLLM()),
        risk_validator=RiskValidator(),
        knowledge_context_builder=context_builder,
        experience_context_service=service,
    )

    current_snapshot = FeatureSnapshot(
        snapshot_id="FS-CURRENT",
        subject_id="B3-PETR4",
        as_of=BASE + timedelta(days=20),
        features=(
            FeatureValue("close", 40.2, FeatureDomain.MARKET, BASE + timedelta(days=20)),
            FeatureValue("volatility_20d", 0.44, FeatureDomain.MARKET, BASE + timedelta(days=20)),
        ),
    )
    current_regime = MarketRegime(
        regime_id="REG-CURRENT",
        as_of=current_snapshot.as_of,
        dimensions=regime().dimensions,
        classifier_version="regime-v1",
        feature_snapshot_id=current_snapshot.snapshot_id,
        confidence=0.8,
    )

    result = workflow.invoke(
        {
            "user_question": "Evaluate PETR4 short put",
            "ticker": "PETR4",
            "as_of": current_snapshot.as_of,
            "feature_snapshot": current_snapshot,
            "market_regime": current_regime,
            "portfolio_context": {"quality_status": "VALIDATED"},
        }
    )

    assert result["experience_retrieval"].matches
    assert result["experience_assessment"].historical_similarity is not None
    assert result["knowledge_context"]["experience_retrieval"] is not None
    assert result["knowledge_context"]["experience_assessment"] is not None
    assert result["decision_proposal"]["action"] == "NO_CHANGE"
    assert result["status"] == "PASS"


def test_workflow_can_run_without_obsidian_or_knowledge_builder():
    workflow = build_workflow(
        reasoning_agent=InvestmentReasoningAgent(FakeLLM()),
        risk_validator=RiskValidator(),
    )
    result = workflow.invoke(
        {
            "user_question": "PETR4",
            "portfolio_context": {"quality_status": "VALIDATED"},
        }
    )

    assert result["evidence"] == []
    assert result["decision_proposal"]["action"] == "NO_CHANGE"


def test_post_outcome_langgraph_learns_and_projects(tmp_path):
    graph = InMemoryKnowledgeGraphStore()
    bridge = MemoryProjectionBridge(
        graph=graph,
        ledger=SQLiteProjectionLedger(tmp_path / "projection.db"),
    )
    service = PostOutcomeLearningService(
        experience_engine=ExperienceEngine(),
        learning_engine=LearningEngine(),
        projection_bridge=bridge,
        cohort_loader=lambda operation, regime: (),
        previous_learning_loader=lambda learning_id: None,
    )
    workflow = build_post_outcome_workflow(service)

    snap = snapshot()
    reg = regime(snap)
    out = outcome()
    event = OutcomeFinalized.from_outcome(out)

    result = workflow.invoke(
        {
            "event": event,
            "operation": operation(),
            "entry_snapshot": snap,
            "regime": reg,
            "outcome": out,
        }
    )

    post = result["result"]
    assert post.experience.operation.operation_id == "OP-001"
    assert post.learning_update.learning.status == LearningStatus.CANDIDATE
    assert graph.get_entity("OP-001") is not None
    assert graph.get_entity(post.learning_update.learning.learning_id) is not None
