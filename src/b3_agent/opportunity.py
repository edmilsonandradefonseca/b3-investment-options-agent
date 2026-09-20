from __future__ import annotations

from dataclasses import dataclass

from .schemas.opportunity import (
    ActionCandidate,
    Opportunity,
    OpportunityAssessment,
    OpportunitySet,
)


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

    @staticmethod
    def _action_candidate(opportunity: Opportunity) -> ActionCandidate:
        return ActionCandidate(
            action_candidate_id=f"ACTION:{opportunity.opportunity_id}",
            action_type=opportunity.action,
            subject_id=opportunity.opportunity_id,
            as_of=opportunity.as_of,
            priority="NORMAL",
            opportunity_refs=(opportunity.opportunity_id,),
            evidence_refs=opportunity.evidence_refs,
            rationale=opportunity.rationale,
            quality_status=opportunity.quality_status,
        )

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
        available_capital: float | None = None,
    ) -> OpportunitySet:
        portfolio_fit = portfolio_fit or {}
        risk = risk or {}
        valuation = valuation or {}
        capital_efficiency = capital_efficiency or {}
        diversification = diversification or {}
        relative_assessment = relative_assessment or {}

        assessments: list[OpportunityAssessment] = []
        action_candidates: list[ActionCandidate] = []
        for opportunity in opportunities:
            reasons: list[str] = []
            if opportunity.quality_status == "REJECTED":
                reasons.append("quality_status=REJECTED")
            elif opportunity.quality_status not in self.policy.quality_order:
                reasons.append(f"unsupported quality_status={opportunity.quality_status}")
            if opportunity.action not in {"BUY", "ACCUMULATE", "SELL_PUT", "SELL_CALL"}:
                reasons.append(f"unsupported action={opportunity.action}")
            if (
                available_capital is not None
                and opportunity.capital_requirement is not None
                and opportunity.capital_requirement > available_capital
            ):
                reasons.append(
                    f"capital_requirement={opportunity.capital_requirement} exceeds "
                    f"available_capital={available_capital}"
                )

            fit = portfolio_fit.get(opportunity.opportunity_id, "UNKNOWN").upper()
            risk_value = risk.get(opportunity.opportunity_id, "UNKNOWN").upper()
            valuation_value = valuation.get(opportunity.opportunity_id, "UNKNOWN").upper()
            capital_value = capital_efficiency.get(opportunity.opportunity_id, "UNKNOWN").upper()
            diversification_value = diversification.get(opportunity.opportunity_id, "UNKNOWN").upper()
            relative_value = relative_assessment.get(opportunity.opportunity_id, "UNKNOWN").upper()

            eligible = not reasons
            expected_return_key = (
                -opportunity.expected_return
                if opportunity.expected_return is not None
                else float("inf")
            )
            ranking_key = (
                self._rank(self.policy.quality_order, opportunity.quality_status),
                self._rank(self.policy.portfolio_fit_order, fit),
                self._rank(self.policy.risk_order, risk_value),
                self._rank(self.policy.valuation_order, valuation_value),
                expected_return_key,
                self._rank(self.policy.capital_efficiency_order, capital_value),
                self._rank(self.policy.diversification_order, diversification_value),
                self._rank(self.policy.relative_order, relative_value),
                opportunity.opportunity_id,
            )
            candidate_ref = f"ACTION:{opportunity.opportunity_id}"
            assessments.append(
                OpportunityAssessment(
                    opportunity_id=opportunity.opportunity_id,
                    eligible=eligible,
                    rejection_reasons=tuple(reasons),
                    attractiveness=valuation_value,
                    portfolio_fit=fit,
                    action_candidate_refs=(candidate_ref,) if eligible else (),
                    ranking_evidence_refs=opportunity.evidence_refs,
                    evidence_refs=opportunity.evidence_refs,
                    ranking_key=ranking_key,
                    rationale=opportunity.rationale,
                    ticker=opportunity.ticker,
                    instrument_type=opportunity.instrument_type,
                    action=opportunity.action,
                    as_of=opportunity.as_of,
                    expected_return=opportunity.expected_return,
                    capital_requirement=opportunity.capital_requirement,
                    liquidity_value=opportunity.liquidity_value,
                    valuation_range_ref=opportunity.valuation_range_ref,
                    options_analysis_ref=opportunity.options_analysis_ref,
                    quant_features_ref=opportunity.quant_features_ref,
                    source_refs=opportunity.source_refs,
                )
            )
            if eligible:
                action_candidates.append(self._action_candidate(opportunity))

        ranked = sorted((a for a in assessments if a.eligible), key=lambda a: a.ranking_key)
        rejected = tuple(a for a in assessments if not a.eligible)
        as_of = max((o.as_of for o in opportunities), default=None)
        if as_of is None:
            from datetime import date
            as_of = date.today()
        quality = "WARNING" if rejected else "VALIDATED"
        source_refs: list[str] = []
        for opportunity in opportunities:
            for source_ref in opportunity.source_refs:
                if source_ref not in source_refs:
                    source_refs.append(source_ref)
        return OpportunitySet(
            as_of=as_of,
            ranked_opportunities=tuple(ranked),
            rejected_opportunities=rejected,
            action_candidates=tuple(action_candidates),
            ranking_policy_version=self.policy.version,
            source_refs=tuple(source_refs),
            quality_status=quality,
        )
