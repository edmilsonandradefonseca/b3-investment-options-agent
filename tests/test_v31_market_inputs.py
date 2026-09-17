from datetime import date, datetime, timezone

from b3_agent.orchestration.market_inputs import build_stock_input_from_brapi
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.valuation import ValuationRange


class FakeBrapi:
    name = "brapi"

    def get_market_data(self, ticker, start, end):
        return [
            StockMarketData(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=datetime(2026, 9, 15, tzinfo=timezone.utc),
                available_timestamp=datetime(2026, 9, 15, 20, tzinfo=timezone.utc),
                source="brapi",
                ingested_at=datetime(2026, 9, 15, 20, tzinfo=timezone.utc),
                source_record_id=f"{ticker}:2026-09-15",
                open=35.0,
                high=36.0,
                low=34.0,
                close=35.5,
                volume=1000000.0,
                currency="BRL",
            )
        ]


def test_brapi_input_boundary_preserves_market_provenance():
    valuation = ValuationRange(
        instrument_id="PETR4",
        ticker="PETR4",
        as_of=date(2026, 9, 15),
        method="test",
        bear_value=30.0,
        base_value=40.0,
        bull_value=50.0,
        source_refs=("valuation:test",),
    )

    result = build_stock_input_from_brapi(
        ticker="petr4",
        start=date(2026, 9, 1),
        end=date(2026, 9, 15),
        valuation=valuation,
        as_of=date(2026, 9, 15),
        adapter=FakeBrapi(),
    )

    assert result.records[0].source == "brapi"
    assert result.records[0].close == 35.5
    assert result.valuation.ticker == "PETR4"
    assert result.source_refs == ("brapi",)


def test_brapi_input_rejects_mismatched_valuation_ticker():
    valuation = ValuationRange(
        instrument_id="VALE3",
        ticker="VALE3",
        as_of=date(2026, 9, 15),
        method="test",
        bear_value=50.0,
        base_value=60.0,
        bull_value=70.0,
    )

    try:
        build_stock_input_from_brapi(
            ticker="PETR4",
            start=date(2026, 9, 1),
            end=date(2026, 9, 15),
            valuation=valuation,
            as_of=date(2026, 9, 15),
            adapter=FakeBrapi(),
        )
    except ValueError as exc:
        assert str(exc) == "valuation ticker must match requested ticker"
    else:
        raise AssertionError("expected ticker mismatch to fail")
