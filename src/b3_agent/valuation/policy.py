from __future__ import annotations

from dataclasses import replace

from b3_agent.schemas.valuation import ValuationRange


class InvestmentPricePolicy:
    """Deterministic price-policy layer applied after fair-value estimation.

    The policy deliberately does not change the underlying valuation. It translates
    the Base/Bull fair values into investor price thresholds using an explicit
    margin-of-safety assumption.
    """

    def apply(
        self,
        valuation: ValuationRange,
        *,
        margin_of_safety: float,
        current_price: float | None = None,
    ) -> ValuationRange:
        if not 0 <= margin_of_safety < 1:
            raise ValueError("margin_of_safety must be between 0 and 1")

        accumulation_price = valuation.base_value * (1.0 - margin_of_safety)
        reduce_price = valuation.base_value
        sell_price = valuation.bull_value

        mos_to_current = None
        if current_price is not None:
            if current_price < 0:
                raise ValueError("current_price cannot be negative")
            if valuation.base_value == 0:
                raise ValueError("base_value must be non-zero to calculate margin_of_safety")
            mos_to_current = (valuation.base_value - current_price) / valuation.base_value

        return replace(
            valuation,
            accumulation_price=accumulation_price,
            reduce_price=reduce_price,
            sell_price=sell_price,
            margin_of_safety=mos_to_current,
            assumptions={
                **valuation.assumptions,
                "policy_margin_of_safety": margin_of_safety,
                "policy_accumulation_anchor": "base_value",
                "policy_reduce_anchor": "base_value",
                "policy_sell_anchor": "bull_value",
                **({"current_price": current_price} if current_price is not None else {}),
            },
        )
