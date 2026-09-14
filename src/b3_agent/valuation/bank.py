from __future__ import annotations

from b3_agent.schemas.valuation import ValuationInputs, ValuationRange


class BankValuationEngine:
    """Deterministic bank valuation using justified P/B from ROE and growth."""

    @staticmethod
    def _value_per_share(
        book_value_per_share: float,
        roe: float,
        cost_of_equity: float,
        terminal_growth_rate: float,
    ) -> float:
        if book_value_per_share <= 0:
            raise ValueError("book_value_per_share must be positive")
        if roe < 0:
            raise ValueError("roe cannot be negative")
        if cost_of_equity <= terminal_growth_rate:
            raise ValueError("cost_of_equity must be greater than terminal_growth_rate")
        justified_pb = (roe - terminal_growth_rate) / (cost_of_equity - terminal_growth_rate)
        return book_value_per_share * justified_pb

    def value_pb_roe(
        self,
        inputs: ValuationInputs,
        *,
        roe_bear: float,
        roe_base: float,
        roe_bull: float,
        cost_of_equity_bear: float,
        cost_of_equity_base: float,
        cost_of_equity_bull: float,
        growth_bear: float,
        growth_base: float,
        growth_bull: float,
    ) -> ValuationRange:
        """Return Bear/Base/Bull equity value per share using justified P/B."""
        if inputs.book_value_per_share is None:
            raise ValueError("book_value_per_share is required for bank valuation")
        scenarios = (
            (roe_bear, cost_of_equity_bear, growth_bear),
            (roe_base, cost_of_equity_base, growth_base),
            (roe_bull, cost_of_equity_bull, growth_bull),
        )
        if any(roe < 0 for roe, _, _ in scenarios):
            raise ValueError("ROE cannot be negative")
        if any(rate <= 0 for _, rate, _ in scenarios):
            raise ValueError("cost of equity must be positive")
        if any(growth < 0 for _, _, growth in scenarios):
            raise ValueError("growth rates cannot be negative")
        if any(rate <= growth for _, rate, growth in scenarios):
            raise ValueError("cost of equity must be greater than growth rate")

        values = tuple(
            self._value_per_share(inputs.book_value_per_share, roe, ke, growth)
            for roe, ke, growth in scenarios
        )
        if not values[0] <= values[1] <= values[2]:
            raise ValueError("Bank scenarios must produce bear <= base <= bull")

        return ValuationRange(
            instrument_id=inputs.instrument_id,
            ticker=inputs.ticker,
            as_of=inputs.as_of,
            method="PB_ROE",
            bear_value=values[0],
            base_value=values[1],
            bull_value=values[2],
            assumptions={
                **inputs.assumptions,
                "book_value_per_share": inputs.book_value_per_share,
                "roe_bear": roe_bear,
                "roe_base": roe_base,
                "roe_bull": roe_bull,
                "cost_of_equity_bear": cost_of_equity_bear,
                "cost_of_equity_base": cost_of_equity_base,
                "cost_of_equity_bull": cost_of_equity_bull,
                "growth_bear": growth_bear,
                "growth_base": growth_base,
                "growth_bull": growth_bull,
            },
            source_refs=inputs.source_refs,
            quality_status=inputs.quality_status,
        )

    def value_bank(self, inputs: ValuationInputs, **kwargs) -> ValuationRange:
        """Backward-compatible alias for value_pb_roe."""
        mapped = {
            "roe_bear": kwargs["roe_bear"],
            "roe_base": kwargs["roe_base"],
            "roe_bull": kwargs["roe_bull"],
            "cost_of_equity_bear": kwargs["cost_of_equity_bear"],
            "cost_of_equity_base": kwargs["cost_of_equity_base"],
            "cost_of_equity_bull": kwargs["cost_of_equity_bull"],
            "growth_bear": kwargs.get("growth_bear", kwargs["terminal_growth_bear"]),
            "growth_base": kwargs.get("growth_base", kwargs["terminal_growth_base"]),
            "growth_bull": kwargs.get("growth_bull", kwargs["terminal_growth_bull"]),
        }
        return self.value_pb_roe(inputs, **mapped)
