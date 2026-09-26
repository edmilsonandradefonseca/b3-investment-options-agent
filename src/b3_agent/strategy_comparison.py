from __future__ import annotations

from hashlib import sha256

from b3_agent.schemas.strategy_comparison import (
    StrategyAlternative,
    StrategyComparison,
)


class StrategyComparisonEngine:
    """Deterministic pairwise comparison without hiding assumptions in a score."""

    def compare(
        self,
        left: StrategyAlternative,
        right: StrategyAlternative,
    ) -> StrategyComparison:
        if left.as_of != right.as_of:
            raise ValueError("strategy alternatives must share the same as_of")

        scenario_names = sorted(
            set(left.payoff_by_scenario) | set(right.payoff_by_scenario)
        )
        scenario_deltas = {}
        for scenario in scenario_names:
            left_value = left.payoff_by_scenario.get(scenario)
            right_value = right.payoff_by_scenario.get(scenario)
            if left_value is None or right_value is None:
                continue
            scenario_deltas[scenario] = right_value - left_value

        digest = sha256(
            f"{left.alternative_id}|{right.alternative_id}|{left.as_of}".encode(
                "utf-8"
            )
        ).hexdigest()[:16]

        quality = "VALIDATED"
        if "REJECTED" in {left.quality_status, right.quality_status}:
            quality = "REJECTED"
        elif "WARNING" in {left.quality_status, right.quality_status}:
            quality = "WARNING"

        return StrategyComparison(
            comparison_id=f"SCMP-{digest}",
            as_of=left.as_of,
            alternatives=(left, right),
            capital_delta=_delta(left.capital_required, right.capital_required),
            expected_return_delta=_delta(
                left.expected_return,
                right.expected_return,
            ),
            max_loss_delta=_delta(left.max_loss, right.max_loss),
            liquidity_delta=_delta(left.liquidity_score, right.liquidity_score),
            portfolio_impact_delta=_delta(
                left.portfolio_impact,
                right.portfolio_impact,
            ),
            historical_similarity_delta=_delta(
                left.historical_similarity,
                right.historical_similarity,
            ),
            experience_confidence_delta=_delta(
                left.experience_confidence,
                right.experience_confidence,
            ),
            scenario_deltas=scenario_deltas,
            assumptions={
                "delta_direction": "right_minus_left",
                "ranking": "not_applied",
                "experience": "kept_separate_from_deterministic_metrics",
            },
            evidence_refs=tuple(
                dict.fromkeys([*left.evidence_refs, *right.evidence_refs])
            ),
            source_refs=tuple(
                dict.fromkeys([*left.source_refs, *right.source_refs])
            ),
            quality_status=quality,
        )


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return right - left
