from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from b3_agent.schemas.position import Position
from .lifecycle import PositionLifecycle, PositionLifecycleEngine


@dataclass(frozen=True)
class PositionAssessment:
    position_id: str
    ticker: str
    underlying_ticker: str
    instrument_type: str
    side: str
    lifecycle: PositionLifecycle
    market_value: float | None
    assignment_capital: float
    deliverable_shares: float


class PositionIntelligenceEngine:
    """Build deterministic per-position intelligence without making trade decisions."""

    def __init__(self, lifecycle_engine: PositionLifecycleEngine | None = None) -> None:
        self.lifecycle_engine = lifecycle_engine or PositionLifecycleEngine()

    def assess(self, positions: tuple[Position, ...], *, as_of: date) -> tuple[PositionAssessment, ...]:
        assessments: list[PositionAssessment] = []
        for position in positions:
            is_option = position.instrument_type == "OPTION"
            side = "LONG" if position.quantity > 0 else "SHORT"
            assignment_capital = 0.0
            deliverable_shares = 0.0
            if is_option:
                option_type = (position.option_type or "").upper()
                if side == "SHORT" and option_type == "PUT":
                    assignment_capital = abs(position.quantity) * (position.strike or 0.0) * position.contract_multiplier
                if side == "SHORT" and option_type == "CALL":
                    deliverable_shares = abs(position.quantity) * position.contract_multiplier
            assessments.append(
                PositionAssessment(
                    position_id=position.position_id,
                    ticker=position.ticker,
                    underlying_ticker=position.underlying_ticker or position.ticker,
                    instrument_type=position.instrument_type,
                    side=side,
                    lifecycle=self.lifecycle_engine.open(position.position_id, as_of),
                    market_value=position.market_value,
                    assignment_capital=assignment_capital,
                    deliverable_shares=deliverable_shares,
                )
            )
        return tuple(assessments)
