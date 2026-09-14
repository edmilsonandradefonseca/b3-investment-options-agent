from __future__ import annotations

from b3_agent.schemas.valuation import ValuationInputs, ValuationRange


class DCFValuationEngine:
    """Deterministic DCF valuation using explicit FCF forecasts and assumptions."""

    @staticmethod
    def _present_value(
        free_cash_flows: tuple[float, ...],
        discount_rate: float,
        terminal_growth_rate: float,
        net_debt: float,
        shares_outstanding: float,
    ) -> float:
        if not free_cash_flows:
            raise ValueError("free_cash_flows cannot be empty")
        if discount_rate <= terminal_growth_rate:
            raise ValueError("discount_rate must be greater than terminal_growth_rate")
        if discount_rate <= 0:
            raise ValueError("discount_rate must be positive")
        if shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")

        pv_forecast = sum(
            fcf / ((1.0 + discount_rate) ** year)
            for year, fcf in enumerate(free_cash_flows, start=1)
        )
        terminal_fcf = free_cash_flows[-1] * (1.0 + terminal_growth_rate)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth_rate)
        pv_terminal = terminal_value / ((1.0 + discount_rate) ** len(free_cash_flows))
        equity_value = pv_forecast + pv_terminal - net_debt
        return equity_value / shares_outstanding

    def value_non_financial(
        self,
        inputs: ValuationInputs,
        *,
        fcf_bear: tuple[float, ...],
        fcf_base: tuple[float, ...],
        fcf_bull: tuple[float, ...],
        discount_rate_bear: float,
        discount_rate_base: float,
        discount_rate_bull: float,
        terminal_growth_bear: float,
        terminal_growth_base: float,
        terminal_growth_bull: float,
    ) -> ValuationRange:
        """Return Bear/Base/Bull equity value per share from explicit DCF scenarios."""
        if inputs.net_debt is None:
            raise ValueError("net_debt is required for DCF valuation")
        if inputs.shares_outstanding is None:
            raise ValueError("shares_outstanding is required for DCF valuation")
        if inputs.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")
        if not fcf_bear or not fcf_base or not fcf_bull:
            raise ValueError("DCF forecast cannot be empty")
        if any(rate <= 0 for rate in (discount_rate_bear, discount_rate_base, discount_rate_bull)):
            raise ValueError("discount rates must be positive")
        if any(growth < 0 for growth in (terminal_growth_bear, terminal_growth_base, terminal_growth_bull)):
            raise ValueError("terminal growth rates cannot be negative")
        if not discount_rate_bear > terminal_growth_bear:
            raise ValueError("discount_rate_bear must be greater than terminal_growth_bear")
        if not discount_rate_base > terminal_growth_base:
            raise ValueError("discount_rate_base must be greater than terminal_growth_base")
        if not discount_rate_bull > terminal_growth_bull:
            raise ValueError("discount_rate_bull must be greater than terminal_growth_bull")
        if not (len(fcf_bear) == len(fcf_base) == len(fcf_bull)):
            raise ValueError("DCF scenarios must use the same forecast horizon")

        values = (
            self._present_value(
                fcf_bear, discount_rate_bear, terminal_growth_bear,
                inputs.net_debt, inputs.shares_outstanding
            ),
            self._present_value(
                fcf_base, discount_rate_base, terminal_growth_base,
                inputs.net_debt, inputs.shares_outstanding
            ),
            self._present_value(
                fcf_bull, discount_rate_bull, terminal_growth_bull,
                inputs.net_debt, inputs.shares_outstanding
            ),
        )
        if not values[0] <= values[1] <= values[2]:
            raise ValueError("DCF scenarios must produce bear <= base <= bull")

        return ValuationRange(
            instrument_id=inputs.instrument_id,
            ticker=inputs.ticker,
            as_of=inputs.as_of,
            method="DCF",
            bear_value=values[0],
            base_value=values[1],
            bull_value=values[2],
            assumptions={
                **inputs.assumptions,
                "fcf_bear": fcf_bear,
                "fcf_base": fcf_base,
                "fcf_bull": fcf_bull,
                "discount_rate_bear": discount_rate_bear,
                "discount_rate_base": discount_rate_base,
                "discount_rate_bull": discount_rate_bull,
                "terminal_growth_bear": terminal_growth_bear,
                "terminal_growth_base": terminal_growth_base,
                "terminal_growth_bull": terminal_growth_bull,
                "net_debt": inputs.net_debt,
                "shares_outstanding": inputs.shares_outstanding,
            },
            source_refs=inputs.source_refs,
            quality_status=inputs.quality_status,
        )
