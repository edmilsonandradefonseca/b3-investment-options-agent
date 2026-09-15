from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionPnl:
    """Deterministic P&L snapshot; realized and unrealized are separate."""

    position_id: str
    unrealized_pnl: float
    realized_pnl: float
    premium_received: float = 0.0
    buyback_cost: float = 0.0

    @property
    def net_option_pnl(self) -> float:
        return self.premium_received - self.buyback_cost + self.realized_pnl + self.unrealized_pnl


class PnlEngine:
    """Calculate deterministic P&L from explicit position inputs."""

    def stock_unrealized(self, *, position_id: str, quantity: float, average_cost: float, market_price: float) -> PositionPnl:
        if quantity == 0:
            raise ValueError("quantity must not be zero")
        if average_cost < 0 or market_price < 0:
            raise ValueError("prices cannot be negative")
        return PositionPnl(
            position_id=position_id,
            unrealized_pnl=(market_price - average_cost) * quantity,
            realized_pnl=0.0,
        )

    def option_snapshot(
        self,
        *,
        position_id: str,
        premium_received: float = 0.0,
        buyback_cost: float = 0.0,
        realized_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
    ) -> PositionPnl:
        for name, value in {
            "premium_received": premium_received,
            "buyback_cost": buyback_cost,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
        }.items():
            if value < 0 and name in {"premium_received", "buyback_cost"}:
                raise ValueError(f"{name} cannot be negative")
        return PositionPnl(
            position_id=position_id,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            premium_received=premium_received,
            buyback_cost=buyback_cost,
        )
