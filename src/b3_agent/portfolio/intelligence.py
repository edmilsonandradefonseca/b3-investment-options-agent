from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict

from b3_agent.schemas.position import PortfolioContext, Position


@dataclass(frozen=True)
class PositionExposure:
    ticker: str
    quantity: float
    market_value: float
    weight: float
    option_count: int
    short_option_count: int
    assignment_capital: float
    covered_call_contracts: float


class PositionIntelligenceEngine:
    """Deterministic exposure and lifecycle context for existing positions."""

    def build_exposures(self, portfolio: PortfolioContext) -> tuple[PositionExposure, ...]:
        grouped: dict[str, list[Position]] = defaultdict(list)
        for position in portfolio.positions:
            underlying = position.underlying_ticker or position.ticker
            grouped[underlying].append(position)

        total_value = sum(p.market_value or 0.0 for p in portfolio.positions) + portfolio.cash
        exposures: list[PositionExposure] = []
        for ticker, positions in sorted(grouped.items()):
            market_value = sum(p.market_value or 0.0 for p in positions)
            option_positions = [p for p in positions if p.instrument_type == "OPTION"]
            short_options = [p for p in option_positions if p.quantity < 0]
            assignment_capital = sum(
                abs(p.quantity) * (p.strike or 0.0) * p.contract_multiplier
                for p in short_options
                if (p.option_type or "").upper() == "PUT"
            )
            covered_call_contracts = sum(
                abs(p.quantity) for p in short_options if (p.option_type or "").upper() == "CALL"
            )
            exposures.append(
                PositionExposure(
                    ticker=ticker,
                    quantity=sum(p.quantity for p in positions if p.instrument_type != "OPTION"),
                    market_value=market_value,
                    weight=(market_value / total_value if total_value else 0.0),
                    option_count=len(option_positions),
                    short_option_count=len(short_options),
                    assignment_capital=assignment_capital,
                    covered_call_contracts=covered_call_contracts,
                )
            )
        return tuple(exposures)
