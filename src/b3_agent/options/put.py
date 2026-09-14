from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PutOpportunity:
    option_id: str
    underlying_ticker: str
    strike: float
    expiration_date: date
    premium: float
    contract_multiplier: float
    effective_price: float
    annualized_return: float
    days_to_expiration: int
    fair_value: float | None = None
    margin_of_safety: float | None = None


class PutAnalysisEngine:
    """Deterministic analysis for cash-secured PUT opportunities."""

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
        fair_value: float | None = None,
    ) -> PutOpportunity:
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
        days = (expiration_date - as_of).days
        if days <= 0:
            raise ValueError("expiration_date must be after as_of")
        if fair_value is not None and fair_value <= 0:
            raise ValueError("fair_value must be positive")

        effective_price = strike - premium
        if effective_price <= 0:
            raise ValueError("premium cannot make effective price non-positive")

        annualized_return = (premium / effective_price) * (365.0 / days)
        margin_of_safety = (
            (fair_value - effective_price) / fair_value
            if fair_value is not None
            else None
        )

        return PutOpportunity(
            option_id=option_id,
            underlying_ticker=underlying_ticker,
            strike=strike,
            expiration_date=expiration_date,
            premium=premium,
            contract_multiplier=contract_multiplier,
            effective_price=effective_price,
            annualized_return=annualized_return,
            days_to_expiration=days,
            fair_value=fair_value,
            margin_of_safety=margin_of_safety,
        )
