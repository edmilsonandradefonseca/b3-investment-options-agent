from __future__ import annotations

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
    records = (adapter or BrapiAdapter()).get_market_data(ticker, start, end)
    if not records:
        raise ValueError(f"no BRAPI observations returned for {ticker.upper()}")

    service = StockOpportunityService()
    effective_records = [
        record
        for record in records
        if service._observation_is_before_or_at(record.observation_timestamp, as_of)
        and record.is_available_at(service._as_datetime(as_of))
    ]
    if not effective_records:
        raise ValueError(
            f"no BRAPI observations for {ticker.upper()} are valid at decision timestamp"
        )

    refs = tuple(dict.fromkeys(("brapi", *source_refs)))
    return StockOpportunityInput(
        records=tuple(effective_records),
        valuation=valuation,
        benchmark_records=tuple(benchmark_records),
        source_refs=refs,
    )
