from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from b3_agent.schemas.experience import ExperienceAssessment, ExperienceRetrievalResult
from b3_agent.schemas.learning import Learning
from b3_agent.schemas.market_regime import MarketRegime
from b3_agent.schemas.scenario import StressResult
from b3_agent.schemas.strategy_comparison import StrategyComparison
from b3_agent.schemas.analysis_run import AnalysisChangeSet


@dataclass(frozen=True)
class DashboardV4View:
    """Read-only presentation contract. It contains no investment calculations."""

    market_regime: dict[str, Any] | None
    experience_assessment: dict[str, Any] | None
    historical_similarity: dict[str, Any] | None
    learnings: tuple[dict[str, Any], ...]
    stress: dict[str, Any] | None
    strategy_comparison: dict[str, Any] | None
    changes: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "market_regime": self.market_regime,
            "experience_assessment": self.experience_assessment,
            "historical_similarity": self.historical_similarity,
            "learnings": list(self.learnings),
            "stress": self.stress,
            "strategy_comparison": self.strategy_comparison,
            "changes": self.changes,
        }


class DashboardV4Presenter:
    """Serialize canonical V4 outputs for Dashboard/Copilot consumption."""

    def build(
        self,
        *,
        market_regime: MarketRegime | None = None,
        experience_assessment: ExperienceAssessment | None = None,
        historical_similarity: ExperienceRetrievalResult | None = None,
        learnings: tuple[Learning, ...] = (),
        stress: StressResult | None = None,
        strategy_comparison: StrategyComparison | None = None,
        changes: AnalysisChangeSet | None = None,
    ) -> DashboardV4View:
        return DashboardV4View(
            market_regime=_serialize(market_regime),
            experience_assessment=_serialize(experience_assessment),
            historical_similarity=_serialize(historical_similarity),
            learnings=tuple(_learning_card(item) for item in learnings),
            stress=_serialize(stress),
            strategy_comparison=_serialize(strategy_comparison),
            changes=_serialize(changes),
        )


def _learning_card(learning: Learning) -> dict[str, Any]:
    return {
        "learning_id": learning.learning_id,
        "statement": learning.statement,
        "status": learning.status.value,
        "scope": learning.learning_scope.value,
        "sample_size": learning.sample_size,
        "recent_sample_size": learning.recent_sample_size,
        "win_rate": learning.win_rate,
        "expected_return": learning.expected_return,
        "confidence": learning.confidence,
        "recent_confidence": learning.recent_confidence,
        "long_term_confidence": learning.long_term_confidence,
        "last_confirmed_at": (
            learning.last_confirmed_at.isoformat()
            if learning.last_confirmed_at is not None
            else None
        ),
        "selection_bias_warning": learning.selection_bias_warning,
        "conditions": list(learning.conditions),
        "regime_ids": list(learning.regime_ids),
        "supporting_evidence": sum(
            link.direction.value == "SUPPORTS" for link in learning.evidence_links
        ),
        "contradicting_evidence": sum(
            link.direction.value == "CONTRADICTS" for link in learning.evidence_links
        ),
    }


def _serialize(value):
    if value is None:
        return None
    return asdict(value)
