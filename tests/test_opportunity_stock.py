from datetime import date

import pytest

from b3_agent.opportunity_stock import StockOpportunityProducer
from b3_agent.schemas.quant import QuantFeatures
from b3_agent.schemas.valuation import ValuationRange


AS_OF = date(2026, 9, 14)


def make_valuation() -> ValuationRange:
    return ValuationRange(
        instrument_id="ABC3",
        ticker="ABC3",
        as_of=AS_OF,
        method="PE",
        bear_value=15.0,
        base_value=20.0,
        bull_value=25.0,
        accumulation_price=16.0,
        reduce_price=20.0,
        sell_price=25.0,
        source_refs=("fundamentals:abc3",),
        quality_status="VALIDATED",
    )


def make_quant() -> QuantFeatures:
    return QuantFeatures(
        instrument_id="ABC3",
        ticker="ABC3",
        as_of=AS_OF,
        return_1d=0.01,
        volatility_20d=0.20,
        sma_20=18.0,
        rsi_14=55.0,
        data_points=60,
        completeness_score=1.0,
        quality_status="VALID",
    )


def test_accumulate_when_price_is_at_accumulation_threshold():
    result = StockOpportunityProducer().produce(
        make_valuation(),
        current_price=16.0,
        quant_features=make_quant(),
    )

    assert len(result) == 1
    opportunity = result[0]

    assert opportunity.action == "ACCUMULATE"
    assert opportunity.ticker == "ABC3"
    assert opportunity.instrument_type == "STOCK"
    assert opportunity.expected_return == pytest.approx(0.25)
    assert opportunity.valuation_range_ref == "valuation:ABC3:PE"
    assert opportunity.quant_features_ref is not None
    assert "fundamentals:abc3" in opportunity.source_refs


def test_buy_between_accumulation_and_reduce_thresholds():
    result = StockOpportunityProducer().produce(
        make_valuation(),
        current_price=18.0,
    )

    assert len(result) == 1
    opportunity = result[0]

    assert opportunity.action == "BUY"
    assert opportunity.expected_return == pytest.approx(
        (20.0 / 18.0) - 1.0
    )
    assert opportunity.quant_features_ref is None


@pytest.mark.parametrize(
    "current_price",
    [20.0, 21.0, 25.0, 30.0],
)
def test_no_stock_opportunity_at_or_above_reduce_threshold(
    current_price: float,
):
    result = StockOpportunityProducer().produce(
        make_valuation(),
        current_price=current_price,
    )

    assert result == ()


def test_rejected_valuation_produces_no_opportunity():
    valuation = ValuationRange(
        instrument_id="ABC3",
        ticker="ABC3",
        as_of=AS_OF,
        method="PE",
        bear_value=15.0,
        base_value=20.0,
        bull_value=25.0,
        accumulation_price=16.0,
        reduce_price=20.0,
        sell_price=25.0,
        source_refs=("fundamentals:abc3",),
        quality_status="REJECTED",
    )

    assert StockOpportunityProducer().produce(
        valuation,
        current_price=15.0,
    ) == ()


def test_preserves_source_refs_without_duplicates():
    result = StockOpportunityProducer().produce(
        make_valuation(),
        current_price=18.0,
        quant_features=make_quant(),
        source_refs=("fundamentals:abc3", "brapi:ABC3"),
    )

    assert result[0].source_refs == (
        "fundamentals:abc3",
        "brapi:ABC3",
    )


def test_requires_positive_current_price():
    with pytest.raises(ValueError, match="current_price must be positive"):
        StockOpportunityProducer().produce(
            make_valuation(),
            current_price=0.0,
        )
