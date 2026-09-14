from __future__ import annotations

from dataclasses import replace

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
        ev_ebitda_bear: float | None = None,
        ev_ebitda_base: float | None = None,
        ev_ebitda_bull: float | None = None,
    ) -> ValuationRange:
        if inputs.earnings_per_share is None:
            raise ValueError("earnings_per_share is required for P/E valuation")
        if any(x < 0 for x in (pe_bear, pe_base, pe_bull)):
            raise ValueError("P/E multiples cannot be negative")
        if not pe_bear <= pe_base <= pe_bull:
            raise ValueError("P/E multiples must satisfy bear <= base <= bull")

        pe_values = tuple(inputs.earnings_per_share * x for x in (pe_bear, pe_base, pe_bull))
        values = list(pe_values)

        # EV/EBITDA is optional in this first MVP because converting EV to
        # equity value requires net debt/share-count inputs not yet in the contract.
        # We therefore retain the parameters for the next contract iteration but
        # do not silently mix enterprise value with equity value.
        if any(x is not None for x in (ev_ebitda_bear, ev_ebitda_base, ev_ebitda_bull)):
            raise NotImplementedError("EV/EBITDA requires net debt and share-count inputs")

        return ValuationRange(
            instrument_id=inputs.instrument_id,
            ticker=inputs.ticker,
            as_of=inputs.as_of,
            method="PE",
            bear_value=values[0],
            base_value=values[1],
            bull_value=values[2],
            assumptions={
                **inputs.assumptions,
                "pe_bear": pe_bear,
                "pe_base": pe_base,
                "pe_bull": pe_bull,
            },
            source_refs=inputs.source_refs,
            quality_status=inputs.quality_status,
        )
