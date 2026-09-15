from __future__ import annotations

from dataclasses import dataclass

from b3_agent.schemas.position import PortfolioContext, Position


@dataclass(frozen=True)
class CapitalRisk:
    cash: float
    put_assignment_capital: float
    total_capital_at_risk: float
    short_option_market_value: float
    put_assignment_ratio: float


class CapitalRiskEngine:
    """Deterministic capital commitments from existing portfolio positions."""

    def assess(self, portfolio: PortfolioContext) -> CapitalRisk:
        puts = [
            p for p in portfolio.positions
            if p.instrument_type == "OPTION"
            and p.quantity < 0
            and (p.option_type or "").upper() == "PUT"
        ]
        assignment = sum(
            abs(p.quantity) * (p.strike or 0.0) * p.contract_multiplier for p in puts
        )
        short_option_value = sum(
            abs(p.market_value or 0.0)
            for p in portfolio.positions
            if p.instrument_type == "OPTION" and p.quantity < 0
        )
        total = portfolio.cash + assignment
        ratio = assignment / portfolio.cash if portfolio.cash else float("inf") if assignment else 0.0
        return CapitalRisk(
            cash=portfolio.cash,
            put_assignment_capital=assignment,
            total_capital_at_risk=total,
            short_option_market_value=short_option_value,
            put_assignment_ratio=ratio,
        )
