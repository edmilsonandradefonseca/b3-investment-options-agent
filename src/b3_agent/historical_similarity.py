from __future__ import annotations
from dataclasses import dataclass
from collections.abc import Iterable
from datetime import datetime
from b3_agent.experience.model import Experience
from b3_agent.experience.retrieval import ExperienceAssessmentEngine, ExperienceRanker
from b3_agent.knowledge.vector_store import VectorSearchResult
from b3_agent.schemas.experience import ExperienceAssessment, ExperienceRetrievalResult
from b3_agent.schemas.feature_snapshot import FeatureSnapshot
from b3_agent.schemas.learning import Learning
from b3_agent.schemas.market_regime import MarketRegime

@dataclass(frozen=True)
class HistoricalSimilaritySnapshot:
    retrieval: ExperienceRetrievalResult
    assessment: ExperienceAssessment

class HistoricalSimilarityService:
    """UC-09 convergence: structured history plus optional semantic candidates."""
    def build(self, *, current_snapshot: FeatureSnapshot, current_regime: MarketRegime, as_of: datetime, experiences: Iterable[Experience]=(), semantic_results: Iterable[VectorSearchResult]=(), learnings: Iterable[Learning]=(), top_k: int=10) -> HistoricalSimilaritySnapshot:
        experience_rows=tuple(experiences); semantic_rows=tuple(semantic_results); learning_rows=tuple(learnings)
        retrieval=ExperienceRanker().rank(current_snapshot=current_snapshot,current_regime=current_regime,as_of=as_of,experiences=experience_rows,semantic_results=semantic_rows,learnings=learning_rows,top_k=top_k)
        assessment=ExperienceAssessmentEngine().assess(retrieval,learnings=learning_rows)
        return HistoricalSimilaritySnapshot(retrieval,assessment)
