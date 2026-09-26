from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections.abc import Callable, Iterable

from b3_agent.experience import ExperienceAssessmentEngine, ExperienceEngine, ExperienceRanker
from b3_agent.experience.events import OutcomeFinalized
from b3_agent.experience.model import Experience
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


@dataclass(frozen=True)
class PreAnalysisExperienceContext:
    retrieval: ExperienceRetrievalResult
    assessment: ExperienceAssessment
    learnings: tuple[Learning, ...]


class ExperienceContextService:
    """Build the V4 PRE-ANALYSIS experience context before specialist reasoning."""

    def __init__(
        self,
        *,
        ranker: ExperienceRanker,
        assessment_engine: ExperienceAssessmentEngine,
        experience_loader: ExperienceLoader,
        learning_loader: LearningLoader,
        semantic_index: LearningSemanticIndex | None = None,
    ) -> None:
        self.ranker = ranker
        self.assessment_engine = assessment_engine
        self.experience_loader = experience_loader
        self.learning_loader = learning_loader
        self.semantic_index = semantic_index

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
        learnings = tuple(self.learning_loader(snapshot.subject_id, as_of))

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
            top_k=top_k,
        )
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
    ) -> None:
        self.experience_engine = experience_engine
        self.learning_engine = learning_engine
        self.projection_bridge = projection_bridge
        self.cohort_loader = cohort_loader
        self.previous_learning_loader = previous_learning_loader

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
        if event.operation_id != operation.operation_id:
            raise ValueError("OutcomeFinalized operation_id mismatch")
        if event.outcome_id != outcome.outcome_id:
            raise ValueError("OutcomeFinalized outcome_id mismatch")

        experience = self.experience_engine.assemble(
            operation=operation,
            entry_snapshot=entry_snapshot,
            market_regime=regime,
            outcome=outcome,
            exit_snapshot=exit_snapshot,
        )

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

        self.projection_bridge.project_operation(
            operation=operation,
            outcome=outcome,
            regime=regime,
        )
        self.projection_bridge.project_learning(update.learning)

        return PostOutcomeResult(
            experience=experience,
            learning_update=update,
        )
