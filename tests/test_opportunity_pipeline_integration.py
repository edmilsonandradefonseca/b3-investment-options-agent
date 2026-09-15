from datetime import date, datetime, timezone

from b3_agent.opportunity_options import OptionsOpportunityProducer
from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.opportunity_stock import StockOpportunityProducer
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.options.put import PutAnalysisEngine
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.valuation import ValuationRange
from b3_agent.stock_opportunity_service import StockOpportunityService


def _stock_record(ticker: str, close: float, observed: datetime) -> StockMarketData:
    return StockMarketData(
        instrument_id=ticker,
        ticker=ticker,
        observation_timestamp=observed,
        available_timestamp=observed,
        source="BRAPI",
        ingested_at=observed,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000_000,
    )


def test_stock_and_options_converge_into_deterministic_opportunity_set():
    as_of = datetime(2026, 9, 11, 23, 59, tzinfo=timezone.utc)
    stock = StockOpportunityService(producer=StockOpportunityProducer())
    valuation = ValuationRange(
        instrument_id="ITUB4",
        ticker="ITUB4",
        as_of=as_of,
        method="PB_ROE",
        bear_value=15.0,
        base_value=20.0,
        bull_value=25.0,
        accumulation_price=16.0,
        reduce_price=20.0,
        sell_price=25.0,
        source_refs=("valuation-engine",),
    )
    stock_opportunities = stock.produce(
        [_stock_record("ITUB4", 15.50, datetime(2026, 9, 11, 17, tzinfo=timezone.utc))],
        valuation,
        as_of=as_of,
        source_refs=("BRAPI",),
    )

    put = PutAnalysisEngine().analyze(
        option_id="ITUBV200",
        underlying_ticker="ITUB4",
        strike=20.0,
        expiration_date=date(2026, 10, 16),
        premium=0.60,
        contract_multiplier=1.0,
        as_of=date(2026, 9, 11),
    )
    options_analysis = OptionsAnalysis(puts=(put,), source_refs=("OPLAB",))
    option_opportunities = OptionsOpportunityProducer().produce(
        options_analysis,
        as_of=as_of,
        source_refs=("OPLAB",),
    )

    pipeline = OpportunityPipeline()
    result = pipeline.build(
        [*stock_opportunities, *option_opportunities],
        as_of=as_of,
        source_refs=("BTG", "BRAPI", "OPLAB"),
    )

    assert result.as_of == as_of
    assert result.quality_status == "VALIDATED"
    assert result.ranking_policy_version == "1.0"
    assert {item.opportunity_id for item in result.ranked_opportunities} == {
        "ACCUMULATE:ITUB4",
        "SELL_PUT:ITUBV200",
    }
    assert result.rejected_opportunities == ()
    assert result.source_refs == ("valuation-engine", "BRAPI", "OPLAB", "BTG")

    stock_assessment = next(
        item for item in result.ranked_opportunities if item.opportunity_id == "ACCUMULATE:ITUB4"
    )
    option_assessment = next(
        item for item in result.ranked_opportunities if item.opportunity_id == "SELL_PUT:ITUBV200"
    )
    assert stock_assessment.ticker == "ITUB4"
    assert stock_assessment.action == "ACCUMULATE"
    assert stock_assessment.expected_return == (20.0 / 15.5) - 1.0
    assert stock_assessment.quant_features_ref == "quant:ITUB4:2026-09-11"
    assert stock_assessment.valuation_range_ref == "valuation:ITUB4:PB_ROE"
    assert option_assessment.ticker == "ITUB4"
    assert option_assessment.action == "SELL_PUT"
    assert option_assessment.options_analysis_ref == "ITUBV200"
