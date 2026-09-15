from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .capital_risk import CapitalRiskEngine, CapitalRiskSnapshot
from .intelligence import PositionExposure, PositionIntelligenceEngine as ExposureEngine
from .position_intelligence import PositionAssessment, PositionIntelligenceEngine as AssessmentEngine
from ..schemas.position import PortfolioContext


@dataclass(frozen=True)
class PortfolioIntelligence:
    """Deterministic portfolio-level context consumed by later decision layers."""

    as_of: date
    assessments: tuple[PositionAssessment, ...]
    exposures: tuple[PositionExposure, ...]
    capital_risk: CapitalRiskSnapshot


class PortfolioIntelligenceEngine:
    """Compose existing deterministic portfolio engines; no trade decisions."""

    def __init__(
        self,
        assessment_engine: AssessmentEngine | None = None,
        exposure_engine: ExposureEngine | None = None,
        capital_risk_engine: CapitalRiskEngine | None = None,
    ) -> None:
        self.assessment_engine = assessment_engine or AssessmentEngine()
        self.exposure_engine = exposure_engine or ExposureEngine()
        self.capital_risk_engine = capital_risk_engine or CapitalRiskEngine()

    def build(self, portfolio: PortfolioContext) -> PortfolioIntelligence:
        return PortfolioIntelligence(
            as_of=portfolio.as_of,
            assessments=self.assessment_engine.assess(portfolio.positions, as_of=portfolio.as_of),
            exposures=self.exposure_engine.build_exposures(portfolio),
            capital_risk=self.capital_risk_engine.assess(portfolio),
        )
