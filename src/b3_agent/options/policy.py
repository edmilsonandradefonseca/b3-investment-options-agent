from __future__ import annotations

from dataclasses import dataclass

from .call import CallOpportunity
from .put import PutOpportunity


@dataclass(frozen=True)
class OptionsPolicy:
    """Deterministic policy thresholds; values are explicit inputs, not hidden rules."""

    min_put_annualized_return: float = 0.0
    min_put_margin_of_safety: float = 0.0
    min_call_annualized_premium_return: float = 0.0
    min_call_total_return_if_assigned: float = 0.0
    max_call_upside_surrendered: float | None = None

    def __post_init__(self) -> None:
        if self.min_put_annualized_return < 0:
            raise ValueError("min_put_annualized_return cannot be negative")
        if not 0 <= self.min_put_margin_of_safety < 1:
            raise ValueError("min_put_margin_of_safety must be between 0 and 1")
        if self.min_call_annualized_premium_return < 0:
            raise ValueError("min_call_annualized_premium_return cannot be negative")
        if self.min_call_total_return_if_assigned < -1:
            raise ValueError("min_call_total_return_if_assigned is invalid")
        if self.max_call_upside_surrendered is not None and self.max_call_upside_surrendered < 0:
            raise ValueError("max_call_upside_surrendered cannot be negative")

    def evaluate_put(self, opportunity: PutOpportunity) -> str:
        if opportunity.margin_of_safety is None:
            return "AVOID"
        if opportunity.margin_of_safety < 0:
            return "AVOID"
        return (
            "SELL_PUT"
            if opportunity.annualized_return >= self.min_put_annualized_return
            and opportunity.margin_of_safety >= self.min_put_margin_of_safety
            else "HOLD_WAIT"
        )

    def evaluate_call(self, opportunity: CallOpportunity) -> str:
        if opportunity.strike <= 0 or opportunity.current_price <= 0:
            return "AVOID"
        if opportunity.annualized_premium_return < self.min_call_annualized_premium_return:
            return "HOLD_WAIT"
        if opportunity.total_return_if_assigned < self.min_call_total_return_if_assigned:
            return "HOLD_WAIT"
        if (
            self.max_call_upside_surrendered is not None
            and opportunity.upside_surrendered is not None
            and opportunity.upside_surrendered > self.max_call_upside_surrendered
        ):
            return "HOLD_WAIT"
        return "SELL_CALL"
