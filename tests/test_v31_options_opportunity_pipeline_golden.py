from datetime import date, datetime, timezone

from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.options.analysis import OptionsAnalysisEngine
from b3_agent.schemas.option import OptionContract, OptionQuote


def test_options_analysis_flows_through_pipeline_into_opportunity_set():
    as_of = date(2026, 9, 16)
    now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    contract = OptionContract(
        option_id="PETR4P300",
        underlying_id="PETR4",
        underlying_ticker="PETR4",
        option_ticker="PETR4P300",
        option_type="PUT",
        strike=30.0,
        expiration_date=date(2026, 10, 16),
    )
    quote = OptionQuote(
        instrument_id="PETR4P300",
        ticker="PETR4P300",
        observation_timestamp=now,
        available_timestamp=now,
        source="oplab",
        ingested_at=now,
        option_id="PETR4P300",
        bid=1.9,
        ask=2.1,
        last=None,
        mid=2.0,
        volume=100.0,
        open_interest=500.0,
    )

    analysis = OptionsAnalysisEngine().analyze_quotes(
        contracts=(contract,),
        quotes=(quote,),
        as_of=as_of,
        source_refs=("oplab",),
    )

    result = OpportunityPipeline().build_from_inputs(
        as_of=as_of,
        options_analyses=(analysis,),
        source_refs=("portfolio_context",),
    )

    assert len(result.ranked_opportunities) == 1
    ranked = result.ranked_opportunities[0]
    assert ranked.opportunity_id == "SELL_PUT:PETR4P300"
    assert ranked.action == "SELL_PUT"
    assert ranked.options_analysis_ref == "PETR4P300"
    assert ranked.source_refs == ("oplab", "portfolio_context")
    assert len(result.action_candidates) == 1
    assert result.action_candidates[0].action_type == "SELL_PUT"
    assert result.quality_status == "VALIDATED"
