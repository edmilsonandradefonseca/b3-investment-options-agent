from __future__ import annotations

from b3_agent.schemas.valuation import ValuationInputs, ValuationRange


class MultiplesValuationEngine:
    """Deterministic valuation using explicit peer/target multiples."""

    def value_non_financial(
        self,
        inputs: ValuationInputs,
        *,
        pe_bear: float,
        pe_base: float,
        pe_bull: float,
    ) -> ValuationRange:
        if inputs.earnings_per_share is None:
            raise ValueError("earnings_per_share is required for P/E valuation")
        if any(x < 0 for x in (pe_bear, pe_base, pe_bull)):
            raise ValueError("P/E multiples cannot be negative")
        if not pe_bear <= pe_base <= pe_bull:
            raise ValueError("P/E multiples must satisfy bear <= base <= bull")

        pe_values = tuple(
            inputs.earnings_per_share * x for x in (pe_bear, pe_base, pe_bull)
        )

        return ValuationRange(
            instrument_id=inputs.instrument_id,
            ticker=inputs.ticker,
            as_of=inputs.as_of,
            method="PE",
            bear_value=pe_values[0],
            base_value=pe_values[1],
            bull_value=pe_values[2],
            assumptions={
                **inputs.assumptions,
                "pe_bear": pe_bear,
                "pe_base": pe_base,
                "pe_bull": pe_bull,
            },
            source_refs=inputs.source_refs,
            quality_status=inputs.quality_status,
        )

    def value_non_financial_ev_ebitda(
        self,
        inputs: ValuationInputs,
        *,
        ev_ebitda_bear: float,
        ev_ebitda_base: float,
        ev_ebitda_bull: float,
    ) -> ValuationRange:
        """Value a non-financial company using EV/EBITDA, converted to equity value per share."""
        if inputs.ebitda is None:
            raise ValueError("ebitda is required for EV/EBITDA valuation")
        if inputs.net_debt is None:
            raise ValueError("net_debt is required for EV/EBITDA valuation")
        if inputs.shares_outstanding is None:
            raise ValueError("shares_outstanding is required for EV/EBITDA valuation")
        if inputs.shares_outstanding <= 0:
            raise ValueError("shares_outstanding must be positive")
        if inputs.ebitda <= 0:
            raise ValueError("ebitda must be positive for EV/EBITDA valuation")
        if any(x < 0 for x in (ev_ebitda_bear, ev_ebitda_base, ev_ebitda_bull)):
            raise ValueError("EV/EBITDA multiples cannot be negative")
        if not ev_ebitda_bear <= ev_ebitda_base <= ev_ebitda_bull:
            raise ValueError("EV/EBITDA multiples must satisfy bear <= base <= bull")

        enterprise_values = tuple(
            inputs.ebitda * x
            for x in (ev_ebitda_bear, ev_ebitda_base, ev_ebitda_bull)
        )
        equity_values_per_share = tuple(
            (enterprise_value - inputs.net_debt) / inputs.shares_outstanding
            for enterprise_value in enterprise_values
        )

        return ValuationRange(
            instrument_id=inputs.instrument_id,
            ticker=inputs.ticker,
            as_of=inputs.as_of,
            method="EV_EBITDA",
            bear_value=equity_values_per_share[0],
            base_value=equity_values_per_share[1],
            bull_value=equity_values_per_share[2],
            assumptions={
                **inputs.assumptions,
                "ev_ebitda_bear": ev_ebitda_bear,
                "ev_ebitda_base": ev_ebitda_base,
                "ev_ebitda_bull": ev_ebitda_bull,
                "net_debt": inputs.net_debt,
                "shares_outstanding": inputs.shares_outstanding,
            },
            source_refs=inputs.source_refs,
            quality_status=inputs.quality_status,
        )
