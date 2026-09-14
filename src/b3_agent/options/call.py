from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CallOpportunity:
    option_id: str
    underlying_ticker: str
    strike: float
    expiration_date: date
    premium: float
    contract_multiplier: float
    current_price: float
    days_to_expiration: int
    premium_return: float
    annualized_premium_return: float
    gain_to_strike: float
    total_return_if_assigned: float
    fair_value: float | None = None
    upside_surrendered: float | None = None
    action: str = "HOLD_WAIT"


class CallAnalysisEngine:
    """Deterministic analysis for covered CALL opportunities."""

    def analyze(
        self,
        *,
        option_id: str,
        underlying_ticker: str,
        strike: float,
        expiration_date: date,
        premium: float,
        contract_multiplier: float,
        as_of: date,
        current_price: float,
        fair_value: float | None = None,
        min_annualized_premium_return: float = 0.0,
        min_total_return_if_assigned: float = 0.0,
        max_upside_surrendered: float | None = None,
    ) -> CallOpportunity:
        if not option_id.strip():
            raise ValueError("option_id must not be empty")
        if not underlying_ticker.strip():
            raise ValueError("underlying_ticker must not be empty")
        if strike <= 0:
            raise ValueError("strike must be positive")
        if premium < 0:
            raise ValueError("premium cannot be negative")
        if contract_multiplier <= 0:
            raise ValueError("contract_multiplier must be positive")
        if current_price <= 0:
            raise ValueError("current_price must be positive")
        if fair_value is not None and fair_value <= 0:
            raise ValueError("fair_value must be positive")
        if min_annualized_premium_return < 0:
            raise ValueError("min_annualized_premium_return cannot be negative")
        if min_total_return_if_assigned < -1:
            raise ValueError("min_total_return_if_assigned is invalid")
        if max_upside_surrendered is not None and max_upside_surrendered < 0:
            raise ValueError("max_upside_surrendered cannot be negative")

        days = (expiration_date - as_of).days
        if days <= 0:
            raise ValueError("expiration_date must be after as_of")

        premium_return = premium / current_price
        annualized_premium_return = premium_return * (365.0 / days)
        gain_to_strike = strike - current_price
        total_return_if_assigned = (strike + premium - current_price) / current_price

        upside_surrendered = (
            max(fair_value - strike, 0.0) if fair_value is not None else None
        )

        meets_return = (
            annualized_premium_return >= min_annualized_premium_return
            and total_return_if_assigned >= min_total_return_if_assigned
        )
        respects_upside = (
            max_upside_surrendered is None
            or upside_surrendered is None
            or upside_surrendered <= max_upside_surrendered
        )
        action = "SELL_CALL" if meets_return and respects_upside else "HOLD_WAIT"

        return CallOpportunity(
            option_id=option_id,
            underlying_ticker=underlying_ticker,
            strike=strike,
            expiration_date=expiration_date,
            premium=premium,
            contract_multiplier=contract_multiplier,
            current_price=current_price,
            days_to_expiration=days,
            premium_return=premium_return,
            annualized_premium_return=annualized_premium_return,
            gain_to_strike=gain_to_strike,
            total_return_if_assigned=total_return_if_assigned,
            fair_value=fair_value,
            upside_surrendered=upside_surrendered,
            action=action,
        )
