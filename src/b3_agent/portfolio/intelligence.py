from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

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
    call_coverage_ratio: float | None = None
    gross_market_value: float = 0.0
    net_market_value: float = 0.0


class PositionIntelligenceEngine:
    """Deterministic exposure and coverage context for existing positions."""

    def build_exposures(self, portfolio: PortfolioContext) -> tuple[PositionExposure, ...]:
        grouped: dict[str, list[Position]] = defaultdict(list)
        for position in portfolio.positions:
            underlying = position.underlying_ticker or position.ticker
            grouped[underlying].append(position)

        total_net_value = sum(p.market_value or 0.0 for p in portfolio.positions) + portfolio.cash
        exposures: list[PositionExposure] = []
        for ticker, positions in sorted(grouped.items()):
            market_value = sum(p.market_value or 0.0 for p in positions)
            gross_market_value = sum(abs(p.market_value or 0.0) for p in positions)
            option_positions = [p for p in positions if p.instrument_type == "OPTION"]
            short_options = [p for p in option_positions if p.quantity < 0]
            puts = [p for p in short_options if (p.option_type or "").upper() == "PUT"]
            calls = [p for p in short_options if (p.option_type or "").upper() == "CALL"]

            assignment_capital = sum(
                abs(p.quantity) * (p.strike or 0.0) * p.contract_multiplier for p in puts
            )
            covered_call_contracts = sum(abs(p.quantity) for p in calls)
            call_deliverable_shares = sum(abs(p.quantity) * p.contract_multiplier for p in calls)
            stock_long_shares = sum(
                p.quantity for p in positions
                if p.instrument_type != "OPTION" and p.quantity > 0
            )
            call_coverage_ratio = (
                stock_long_shares / call_deliverable_shares
                if call_deliverable_shares
                else None
            )

            exposures.append(
                PositionExposure(
                    ticker=ticker,
                    quantity=sum(p.quantity for p in positions if p.instrument_type != "OPTION"),
                    market_value=market_value,
                    weight=(market_value / total_net_value if total_net_value else 0.0),
                    option_count=len(option_positions),
                    short_option_count=len(short_options),
                    assignment_capital=assignment_capital,
                    covered_call_contracts=covered_call_contracts,
                    call_coverage_ratio=call_coverage_ratio,
                    gross_market_value=gross_market_value,
                    net_market_value=market_value,
                )
            )
        return tuple(exposures)
