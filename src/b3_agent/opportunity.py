from __future__ import annotations

from dataclasses import dataclass

from .schemas.opportunity import Opportunity, OpportunityAssessment, OpportunitySet


@dataclass(frozen=True)
class RankingPolicy:
    version: str = "1.0"

    quality_order: tuple[str, ...] = ("VALIDATED", "WARNING")
    portfolio_fit_order: tuple[str, ...] = ("GOOD", "NEUTRAL", "WARNING", "POOR")
    risk_order: tuple[str, ...] = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    valuation_order: tuple[str, ...] = ("ATTRACTIVE", "FAIR", "EXPENSIVE", "UNKNOWN")
    capital_efficiency_order: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
    diversification_order: tuple[str, ...] = ("IMPROVES", "NEUTRAL", "WORSENS", "UNKNOWN")
    relative_order: tuple[str, ...] = ("SUPERIOR", "NEUTRAL", "INFERIOR", "UNKNOWN")


class OpportunityIntelligenceEngine:
    """Deterministic convergence and ranking layer; never executes trades."""

    def __init__(self, policy: RankingPolicy | None = None) -> None:
        self.policy = policy or RankingPolicy()

    @staticmethod
    def _rank(mapping: tuple[str, ...], value: str | None) -> int:
        normalized = (value or "UNKNOWN").upper()
        try:
            return mapping.index(normalized)
        except ValueError:
            return len(mapping)

    def assess(
        self,
        opportunities: tuple[Opportunity, ...],
        *,
        portfolio_fit: dict[str, str] | None = None,
        risk: dict[str, str] | None = None,
        valuation: dict[str, str] | None = None,
        capital_efficiency: dict[str, str] | None = None,
        diversification: dict[str, str] | None = None,
        relative_assessment: dict[str, str] | None = None,
    ) -> OpportunitySet:
        portfolio_fit = portfolio_fit or {}
        risk = risk or {}
        valuation = valuation or {}
        capital_efficiency = capital_efficiency or {}
        diversification = diversification or {}
        relative_assessment = relative_assessment or {}

        assessments: list[OpportunityAssessment] = []
        for opportunity in opportunities:
            reasons: list[str] = []
            if opportunity.quality_status == "REJECTED":
                reasons.append("quality_status=REJECTED")
            elif opportunity.quality_status not in self.policy.quality_order:
                reasons.append(f"unsupported quality_status={opportunity.quality_status}")
            if opportunity.action not in {"BUY", "ACCUMULATE", "SELL_PUT", "SELL_CALL"}:
                reasons.append(f"unsupported action={opportunity.action}")

            fit = portfolio_fit.get(opportunity.opportunity_id, "UNKNOWN").upper()
            risk_value = risk.get(opportunity.opportunity_id, "UNKNOWN").upper()
            valuation_value = valuation.get(opportunity.opportunity_id, "UNKNOWN").upper()
            capital_value = capital_efficiency.get(opportunity.opportunity_id, "UNKNOWN").upper()
            diversification_value = diversification.get(opportunity.opportunity_id, "UNKNOWN").upper()
            relative_value = relative_assessment.get(opportunity.opportunity_id, "UNKNOWN").upper()

            eligible = not reasons
            ranking_key = (
                self._rank(self.policy.quality_order, opportunity.quality_status),
                self._rank(self.policy.portfolio_fit_order, fit),
                self._rank(self.policy.risk_order, risk_value),
                self._rank(self.policy.valuation_order, valuation_value),
                self._rank(self.policy.capital_efficiency_order, capital_value),
                self._rank(self.policy.diversification_order, diversification_value),
                self._rank(self.policy.relative_order, relative_value),
                -(opportunity.expected_return if opportunity.expected_return is not None else float("inf")),
                opportunity.opportunity_id,
            )
            assessments.append(
                OpportunityAssessment(
                    opportunity_id=opportunity.opportunity_id,
                    eligible=eligible,
                    rejection_reasons=tuple(reasons),
                    attractiveness=valuation_value,
                    portfolio_fit=fit,
                    ranking_evidence_refs=opportunity.evidence_refs,
                    evidence_refs=opportunity.evidence_refs,
                    ranking_key=ranking_key,
                    rationale=opportunity.rationale,
                )
            )

        ranked = sorted((a for a in assessments if a.eligible), key=lambda a: a.ranking_key)
        rejected = tuple(a for a in assessments if not a.eligible)
        as_of = max((o.as_of for o in opportunities), default=None)
        if as_of is None:
            from datetime import date
            as_of = date.today()
        quality = "WARNING" if rejected else "VALIDATED"
        return OpportunitySet(
            as_of=as_of,
            ranked_opportunities=tuple(ranked),
            rejected_opportunities=rejected,
            ranking_policy_version=self.policy.version,
            source_refs=tuple(sorted({ref for o in opportunities for ref in o.source_refs})),
            quality_status=quality,
        )
