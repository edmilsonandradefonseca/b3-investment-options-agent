from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.stock_opportunity_service import StockOpportunityService
from b3_agent.schemas.valuation import ValuationRange
from b3_agent.opportunity_pipeline import StockOpportunityInput

AS_OF = date | datetime


def load_brapi_stock_input(
    *,
    ticker: str,
    start: date,
    end: date,
    valuation: ValuationRange,
    as_of: AS_OF,
    adapter: BrapiAdapter | None = None,
    benchmark_records=(),
    source_refs: tuple[str, ...] = (),
) -> StockOpportunityInput:
    """Acquire BRAPI observations and return the typed deterministic stock input.

    Acquisition stays behind the BRAPI adapter. This function does not rank,
    reason, call an LLM, or make a portfolio decision.
    """
    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        raise ValueError("ticker must not be empty")

    records = (adapter or BrapiAdapter()).get_market_data(
        normalized_ticker, start, end
    )
    if not records:
        raise ValueError(f"no BRAPI observations returned for {normalized_ticker}")

    service = StockOpportunityService()
    effective_records = [
        record
        for record in records
        if service._observation_is_before_or_at(record.observation_timestamp, as_of)
        and record.is_available_at(service._as_datetime(as_of))
    ]
    if not effective_records:
        raise ValueError(
            f"no BRAPI observations for {normalized_ticker} are valid at decision timestamp"
        )

    normalized_records = tuple(
        replace(record, ticker=normalized_ticker) for record in effective_records
    )
    refs = tuple(dict.fromkeys(("brapi", *source_refs)))
    return StockOpportunityInput(
        records=normalized_records,
        valuation=valuation,
        benchmark_records=tuple(benchmark_records),
        source_refs=refs,
    )
