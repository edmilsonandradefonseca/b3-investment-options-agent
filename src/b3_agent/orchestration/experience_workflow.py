from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from collections.abc import Callable, Iterable
from typing import Protocol, TypedDict
from hashlib import sha256
import json

from langgraph.graph import END, START, StateGraph

from b3_agent.experience import ExperienceAssessmentEngine, ExperienceEngine, ExperienceRanker
from b3_agent.experience.events import OutcomeFinalized
from b3_agent.experience.model import Experience
from b3_agent.experience.retrieval import experience_available_for_analysis, learning_available_for_analysis
from b3_agent.knowledge.learning_semantic import LearningSemanticIndex
from b3_agent.knowledge.projection import MemoryProjectionBridge
from b3_agent.learning import LearningEngine, LearningUpdateResult
from b3_agent.schemas.experience import ExperienceAssessment, ExperienceRetrievalResult
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.learning import Learning
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.schemas.operation import Operation
from b3_agent.schemas.outcome import Outcome


ExperienceLoader = Callable[[str, datetime], Iterable[Experience]]
LearningLoader = Callable[[str, datetime], Iterable[Learning]]
PreviousLearningLoader = Callable[[str], Learning | None]
CohortLoader = Callable[[Operation, MarketRegime], Iterable[Experience]]
RetrievalTraceSink = Callable[[ExperienceRetrievalResult], None]


@dataclass(frozen=True)
class PreAnalysisExperienceContext:
    retrieval: ExperienceRetrievalResult
    assessment: ExperienceAssessment
    learnings: tuple[Learning, ...]

    def as_payload(self) -> dict:
        visible = []
        for learning in self.learnings[:20]:
            item = asdict(learning)
            item["evidence_links"] = item["evidence_links"][:20]
            item["evidence_details_omitted"] = max(0, len(learning.evidence_links)-20)
            item["source_refs"] = item["source_refs"][:20]
            item["source_details_omitted"] = max(0, len(learning.source_refs)-20)
            visible.append(item)
        return {
            "status": "AVAILABLE" if self.retrieval.matches else "NO_ELIGIBLE_PRECEDENTS",
            "assessment": asdict(self.assessment), "retrieval": asdict(self.retrieval),
            "learnings": visible, "learning_details_omitted": max(0, len(self.learnings)-20),
        }


class ExperienceContextService:
    """Build the V4 PRE-ANALYSIS experience context before specialist reasoning.

    Injected loaders must resolve actual canonical versions and enforce their
    commit/ingestion availability at as_of. Domain finalized/updated timestamps
    alone cannot prove when a historical object became available to the system.
    """

    def __init__(
        self,
        *,
        ranker: ExperienceRanker,
        assessment_engine: ExperienceAssessmentEngine,
        experience_loader: ExperienceLoader,
        learning_loader: LearningLoader,
        semantic_index: LearningSemanticIndex | None = None,
        retrieval_trace_sink: RetrievalTraceSink | None = None,
    ) -> None:
        self.ranker = ranker
        self.assessment_engine = assessment_engine
        self.experience_loader = experience_loader
        self.learning_loader = learning_loader
        self.semantic_index = semantic_index
        self.retrieval_trace_sink = retrieval_trace_sink

    def build(
        self,
        *,
        query: str,
        snapshot: FeatureSnapshot,
        regime: MarketRegime,
        as_of: datetime,
        ticker: str | None = None,
        top_k: int = 10,
    ) -> PreAnalysisExperienceContext:
        experiences = tuple(self.experience_loader(snapshot.subject_id, as_of))
        learnings = tuple(
            item for item in self.learning_loader(snapshot.subject_id, as_of)
            if learning_available_for_analysis(item, as_of=as_of, subject_id=snapshot.subject_id)
        )

        semantic_results = ()
        if self.semantic_index is not None:
            semantic_results = self.semantic_index.search(
                query,
                as_of=as_of,
                ticker=ticker,
                top_k=top_k,
            )

        retrieval = self.ranker.rank(
            current_snapshot=snapshot,
            current_regime=regime,
            as_of=as_of,
            experiences=experiences,
            semantic_results=semantic_results,
            learnings=learnings,
            top_k=top_k,
        )
        if self.retrieval_trace_sink is not None:
            self.retrieval_trace_sink(retrieval)
        assessment = self.assessment_engine.assess(
            retrieval,
            learnings=learnings,
        )
        return PreAnalysisExperienceContext(
            retrieval=retrieval,
            assessment=assessment,
            learnings=learnings,
        )


@dataclass(frozen=True)
class PostOutcomeResult:
    experience: Experience
    learning_update: LearningUpdateResult


@dataclass(frozen=True)
class CanonicalPostOutcomeCommit:
    event: OutcomeFinalized
    input_fingerprint: str
    committed_at: datetime
    result: PostOutcomeResult


class CanonicalPostOutcomeStore(Protocol):
    """Adapter to the actual canonical owner, never a memory projection store.

    commit must atomically persist the experience/learning version and consume
    the event key, comparing expected_previous for optimistic concurrency.
    Repeated event keys return the original commit; conflicting payloads,
    duplicate economic identities and stale previous versions must fail.
    The owner must independently establish terminal/source/coverage authority.
    This protocol does not create a database or authorize source inference.
    """
    def load(self, event: OutcomeFinalized) -> CanonicalPostOutcomeCommit | None: ...

    def commit(
        self, *, event: OutcomeFinalized, input_fingerprint: str,
        result: PostOutcomeResult, expected_previous: Learning | None,
    ) -> CanonicalPostOutcomeCommit: ...


def _post_outcome_fingerprint(event, experience):
    def encode(value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"Unsupported canonical value: {type(value).__name__}")
    payload = json.dumps([asdict(event), asdict(experience)], sort_keys=True, allow_nan=False, default=encode)
    return sha256(payload.encode("utf-8")).hexdigest()


class PostOutcomeLearningService:
    """Canonical V4 POST-OUTCOME path triggered by OutcomeFinalized."""

    def __init__(
        self,
        *,
        experience_engine: ExperienceEngine,
        learning_engine: LearningEngine,
        projection_bridge: MemoryProjectionBridge,
        cohort_loader: CohortLoader,
        previous_learning_loader: PreviousLearningLoader,
        canonical_store: CanonicalPostOutcomeStore | None = None,
    ) -> None:
        self.experience_engine = experience_engine
        self.learning_engine = learning_engine
        self.projection_bridge = projection_bridge
        self.cohort_loader = cohort_loader
        self.previous_learning_loader = previous_learning_loader
        self.canonical_store = canonical_store

    def handle(
        self,
        *,
        event: OutcomeFinalized,
        operation: Operation,
        entry_snapshot: FeatureSnapshot,
        regime: MarketRegime,
        outcome: Outcome,
        exit_snapshot: FeatureSnapshot | None = None,
    ) -> PostOutcomeResult:
        if self.canonical_store is None:
            raise RuntimeError("POST-OUTCOME requires an authoritative canonical store adapter")
        if event != OutcomeFinalized.from_outcome(outcome):
            raise ValueError("OutcomeFinalized identity/version/time mismatch")
        if event.operation_id != operation.operation_id:
            raise ValueError("OutcomeFinalized operation_id mismatch")
        if entry_snapshot.as_of != operation.opened_at:
            raise ValueError("entry snapshot must represent the operation entry time")
        if entry_snapshot.subject_id not in {operation.underlying_id, *operation.instrument_ids}:
            raise ValueError("entry snapshot subject does not belong to operation")
        for linked, actual, label in (
            (operation.entry_snapshot_id, entry_snapshot.snapshot_id, "entry snapshot"),
            (operation.outcome_id, outcome.outcome_id, "outcome"),
            (operation.exit_snapshot_id, exit_snapshot.snapshot_id if exit_snapshot else None, "exit snapshot"),
        ):
            if linked is not None and linked != actual:
                raise ValueError(f"operation {label} link mismatch")

        experience = self.experience_engine.assemble(
            operation=operation,
            entry_snapshot=entry_snapshot,
            market_regime=regime,
            outcome=outcome,
            exit_snapshot=exit_snapshot,
        )
        if not experience_available_for_analysis(experience, as_of=event.occurred_at):
            raise ValueError("POST-OUTCOME requires a final valid experience available at event time")
        fingerprint = _post_outcome_fingerprint(event, experience)
        existing = self.canonical_store.load(event)
        if existing is not None:
            return self._project_committed(existing, event, fingerprint, experience)

        cohort = list(self.cohort_loader(operation, regime))
        if all(item.experience_id != experience.experience_id for item in cohort):
            cohort.append(experience)

        provisional = self.learning_engine.learn(
            cohort,
            as_of=event.occurred_at,
        )
        previous = self.previous_learning_loader(provisional.learning.learning_id)

        update = self.learning_engine.learn(
            cohort,
            as_of=event.occurred_at,
            previous=previous,
        )

        proposed = PostOutcomeResult(
            experience=experience,
            learning_update=update,
        )
        committed = self.canonical_store.commit(
            event=event, input_fingerprint=fingerprint, result=proposed,
            expected_previous=previous,
        )
        return self._project_committed(committed, event, fingerprint, experience)

    def _project_committed(self, committed, event, fingerprint, experience):
        if not isinstance(committed, CanonicalPostOutcomeCommit):
            raise ValueError("canonical commit receipt is required before projection")
        if committed.event != event or committed.input_fingerprint != fingerprint:
            raise ValueError("canonical commit event/input conflict")
        if committed.result.experience != experience:
            raise ValueError("canonical commit experience mismatch")
        if committed.committed_at.tzinfo is None or committed.committed_at.utcoffset() is None or committed.committed_at < event.occurred_at:
            raise ValueError("canonical commit timestamp must follow the event")
        learning = committed.result.learning_update.learning
        if not learning_available_for_analysis(learning, as_of=event.occurred_at) or learning.last_updated_at != event.occurred_at:
            raise ValueError("canonical commit learning version is not available at event time")
        if experience.experience_id not in learning.source_refs or learning.sample_size != committed.result.learning_update.statistics.sample_size:
            raise ValueError("canonical commit learning evidence/sample mismatch")
        self.projection_bridge.project_operation(
            operation=committed.result.experience.operation,
            outcome=committed.result.experience.outcome,
            regime=committed.result.experience.market_regime,
        )
        self.projection_bridge.project_learning(committed.result.learning_update.learning)
        return committed.result



class PostOutcomeState(TypedDict, total=False):
    event: OutcomeFinalized
    operation: Operation
    entry_snapshot: FeatureSnapshot
    regime: MarketRegime
    outcome: Outcome
    exit_snapshot: FeatureSnapshot | None
    result: PostOutcomeResult


def build_post_outcome_workflow(service: PostOutcomeLearningService):
    """Build the canonical asynchronous V4 POST-OUTCOME LangGraph."""

    def learn_from_outcome(state: PostOutcomeState):
        required = ("event", "operation", "entry_snapshot", "regime", "outcome")
        missing = [name for name in required if name not in state]
        if missing:
            raise ValueError(f"post-outcome workflow missing: {missing}")
        result = service.handle(
            event=state["event"],
            operation=state["operation"],
            entry_snapshot=state["entry_snapshot"],
            regime=state["regime"],
            outcome=state["outcome"],
            exit_snapshot=state.get("exit_snapshot"),
        )
        return {"result": result}

    graph = StateGraph(PostOutcomeState)
    graph.add_node("learn_from_outcome", learn_from_outcome)
    graph.add_edge(START, "learn_from_outcome")
    graph.add_edge("learn_from_outcome", END)
    return graph.compile()
