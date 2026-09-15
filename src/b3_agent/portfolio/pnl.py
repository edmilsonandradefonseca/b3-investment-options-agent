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
        return PositionPnl(position_id, (market_price - average_cost) * quantity, 0.0)

    def option_snapshot(
        self, *, position_id: str, premium_received: float = 0.0,
        buyback_cost: float = 0.0, realized_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
    ) -> PositionPnl:
        if premium_received < 0 or buyback_cost < 0:
            raise ValueError("premium_received and buyback_cost cannot be negative")
        return PositionPnl(position_id, unrealized_pnl, realized_pnl, premium_received, buyback_cost)

    def option_from_quotes(
        self, *, position_id: str, quantity: float, opening_price: float,
        current_price: float, contract_multiplier: float = 1.0,
        premium_received: float = 0.0, realized_pnl: float = 0.0,
    ) -> PositionPnl:
        """Mark an option position from explicit opening/current prices.

        For a long position, price movement is (current-opening)*quantity.
        For a short position, the signed quantity reverses the mark-to-market.
        Premium received is kept separate and is not inferred from market value.
        """
        if quantity == 0:
            raise ValueError("quantity must not be zero")
        if opening_price < 0 or current_price < 0:
            raise ValueError("option prices cannot be negative")
        if contract_multiplier <= 0:
            raise ValueError("contract_multiplier must be positive")
        if premium_received < 0:
            raise ValueError("premium_received cannot be negative")
        unrealized = (current_price - opening_price) * quantity * contract_multiplier
        return PositionPnl(position_id, unrealized, realized_pnl, premium_received, 0.0)
