from __future__ import annotations

from dataclasses import dataclass

from b3_agent.schemas.position import PortfolioContext


@dataclass(frozen=True)
class CapitalRiskSnapshot:
    """Deterministic capital-at-risk view for existing portfolio positions."""

    cash: float
    assignment_capital: float
    cash_after_assignment: float
    fully_cash_secured: bool
    uncovered_call_shares: float


class CapitalRiskEngine:
    """Calculate capital requirements without producing or executing orders."""

    def assess(self, portfolio: PortfolioContext) -> CapitalRiskSnapshot:
        assignment_capital = 0.0
        uncovered_call_shares = 0.0

        grouped: dict[str, dict[str, float]] = {}
        for position in portfolio.positions:
            underlying = position.underlying_ticker or position.ticker
            bucket = grouped.setdefault(underlying, {"stock_shares": 0.0, "call_shares": 0.0})
            if position.instrument_type != "OPTION" and position.quantity > 0:
                bucket["stock_shares"] += position.quantity
            if position.instrument_type == "OPTION" and position.quantity < 0:
                option_type = (position.option_type or "").upper()
                if option_type == "PUT":
                    assignment_capital += (
                        abs(position.quantity) * (position.strike or 0.0) * position.contract_multiplier
                    )
                elif option_type == "CALL":
                    bucket["call_shares"] += abs(position.quantity) * position.contract_multiplier

        for bucket in grouped.values():
            uncovered_call_shares += max(0.0, bucket["call_shares"] - bucket["stock_shares"])

        cash_after_assignment = portfolio.cash - assignment_capital
        return CapitalRiskSnapshot(
            cash=portfolio.cash,
            assignment_capital=assignment_capital,
            cash_after_assignment=cash_after_assignment,
            fully_cash_secured=cash_after_assignment >= 0.0,
            uncovered_call_shares=uncovered_call_shares,
        )
