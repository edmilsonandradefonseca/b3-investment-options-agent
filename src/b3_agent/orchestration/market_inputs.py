from __future__ import annotations

from datetime import date, datetime

from b3_agent.opportunity_pipeline import StockOpportunityInput
from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.schemas.valuation import ValuationRange

AS_OF = date | datetime


def build_stock_input_from_brapi(
    *,
    ticker: str,
    start: date,
    end: date,
    valuation: ValuationRange,
    as_of: AS_OF,
    adapter: BrapiAdapter | None = None,
    benchmark_ticker: str | None = None,
) -> StockOpportunityInput:
    """Build a deterministic stock input from the BRAPI adapter.

    BRAPI remains the market-information provider. No valuation, ranking, LLM
    reasoning, or portfolio decision is performed here.
    """
    if valuation.ticker.upper() != ticker.upper():
        raise ValueError("valuation ticker must match requested ticker")

    provider = adapter or BrapiAdapter()
    records = tuple(provider.get_market_data(ticker, start, end))
    if not records:
        raise ValueError(f"BRAPI returned no records for {ticker}")

    benchmark_records = ()
    if benchmark_ticker:
        benchmark_records = tuple(
            provider.get_market_data(benchmark_ticker, start, end)
        )

    return StockOpportunityInput(
        records=records,
        valuation=valuation,
        benchmark_records=benchmark_records,
        source_refs=(provider.name,),
    )
