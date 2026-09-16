from datetime import date, datetime, timezone

from b3_agent.orchestration.provider_inputs import load_brapi_stock_input
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.valuation import ValuationRange


class FakeBrapi:
    def get_market_data(self, ticker, start, end):
        observation = datetime(2026, 9, 15, 17, 0, tzinfo=timezone.utc)
        return [
            StockMarketData(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=observation,
                available_timestamp=datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc),
                source="brapi",
                ingested_at=datetime(2026, 9, 15, 18, 0, tzinfo=timezone.utc),
                source_record_id=f"{ticker}:1",
                open=10.0,
                high=11.0,
                low=9.0,
                close=10.5,
                volume=1000.0,
                currency="BRL",
            )
        ]


def test_brapi_input_is_typed_and_point_in_time_filtered():
    valuation = ValuationRange(
        instrument_id="PETR4",
        ticker="PETR4",
        as_of=date(2026, 9, 15),
        method="golden",
        bear_value=9.0,
        base_value=10.5,
        bull_value=12.0,
    )
    result = load_brapi_stock_input(
        ticker="petr4",
        start=date(2026, 9, 1),
        end=date(2026, 9, 15),
        valuation=valuation,
        as_of=date(2026, 9, 15),
        adapter=FakeBrapi(),
    )
    assert result.records[0].ticker == "PETR4"
    assert result.records[0].source == "brapi"
    assert result.source_refs == ("brapi",)
