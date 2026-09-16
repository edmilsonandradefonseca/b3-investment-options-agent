from __future__ import annotations

from datetime import date, datetime, timezone

from b3_agent.opportunity_pipeline import OpportunityPipeline, StockOpportunityInput
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.opportunity import Opportunity
from b3_agent.schemas.valuation import ValuationRange


def test_v31_opportunity_producer_converges_stock_and_option_candidates() -> None:
    as_of = datetime(2026, 9, 11, 20, 0, tzinfo=timezone.utc)
    stock = StockOpportunityInput(
        records=(
            StockMarketData(
                instrument_id="PETR4",
                ticker="PETR4",
                observation_timestamp=datetime(2026, 9, 10, 20, tzinfo=timezone.utc),
                available_timestamp=datetime(2026, 9, 10, 20, tzinfo=timezone.utc),
                source="BRAPI",
                ingested_at=datetime(2026, 9, 10, 20, 1, tzinfo=timezone.utc),
                open=39.0,
                high=41.0,
                low=38.0,
                close=40.0,
                volume=1_000_000.0,
            ),
        ),
        valuation=ValuationRange(
            ticker="PETR4",
            method="TEST",
            as_of=date(2026, 9, 11),
            base_value=50.0,
            low_value=45.0,
            high_value=55.0,
            accumulation_price=42.0,
            reduce_price=60.0,
            source_refs=("valuation:test",),
            quality_status="VALIDATED",
        ),
        source_refs=("BRAPI",),
    )
    stock_result = OpportunityPipeline().build_from_inputs(
        as_of=as_of,
        stock_inputs=(stock,),
    )

    assert stock_result.quality_status == "VALIDATED"
    assert stock_result.source_refs == ("BRAPI", "valuation:test")
    assert len(stock_result.ranked_opportunities) == 1
    assert stock_result.ranked_opportunities[0].action == "ACCUMULATE"
    assert len(stock_result.action_candidates) == 1
    assert stock_result.action_candidates[0].action_type == "ACCUMULATE"

    option = Opportunity(
        opportunity_id="SELL_CALL:PETR4-TEST",
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_CALL",
        as_of=as_of,
        expected_return=0.12,
        capital_requirement=100.0,
        evidence_refs=("options:PETR4-TEST",),
        source_refs=("OPLAB",),
        quality_status="VALIDATED",
        rationale="Deterministic option test opportunity.",
    )
    stock_opportunity = Opportunity(
        opportunity_id="PETR4:ACCUMULATE:TEST",
        ticker="PETR4",
        instrument_type="STOCK",
        action="ACCUMULATE",
        as_of=as_of,
        expected_return=0.25,
        evidence_refs=("valuation:PETR4:TEST",),
        source_refs=("BRAPI",),
        quality_status="VALIDATED",
    )

    combined = OpportunityPipeline().build(
        opportunities=(stock_opportunity, option),
        as_of=as_of,
    )

    assert {item.instrument_type for item in combined.ranked_opportunities} == {"STOCK", "OPTION"}
    assert combined.source_refs == ("BRAPI", "OPLAB")
    assert {item.action_type for item in combined.action_candidates} == {"ACCUMULATE", "SELL_CALL"}
