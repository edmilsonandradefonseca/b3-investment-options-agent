from __future__ import annotations

from datetime import datetime, timezone, date

from b3_agent.orchestration.live_providers import LiveProviderService
from b3_agent.providers.oplab.options import OplabOptionsAdapter
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.option import OptionContract, OptionQuote


class FakeMarketProvider:
    name = "brapi"

    def get_market_data(self, ticker, start, end):
        now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
        return [
            StockMarketData(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=now,
                available_timestamp=now,
                source=self.name,
                ingested_at=now,
                source_record_id=f"{ticker}:market",
                open=28.0,
                high=30.0,
                low=27.5,
                close=29.0,
                volume=1_000_000,
                currency="BRL",
            )
        ]


class FakeOptionsProvider:
    name = "oplab"

    def get_options(self, ticker, as_of):
        return [
            OptionContract(
                option_id="PETRV300",
                underlying_id=ticker,
                underlying_ticker=ticker,
                option_ticker="PETRV300",
                option_type="PUT",
                strike=30.0,
                expiration_date=date(2026, 10, 16),
            ),
            OptionContract(
                option_id="PETRJ320",
                underlying_id=ticker,
                underlying_ticker=ticker,
                option_ticker="PETRJ320",
                option_type="CALL",
                strike=32.0,
                expiration_date=date(2026, 10, 16),
            ),
        ]

    def get_option_quotes(self, ticker, as_of):
        return [
            OptionQuote(
                instrument_id="PETRV300",
                ticker=ticker,
                observation_timestamp=as_of,
                available_timestamp=as_of,
                source=self.name,
                ingested_at=as_of,
                option_id="PETRV300",
                bid=1.0,
                ask=1.2,
                last=1.1,
                mid=1.1,
                volume=1000,
                open_interest=5000,
            ),
            OptionQuote(
                instrument_id="PETRJ320",
                ticker=ticker,
                observation_timestamp=as_of,
                available_timestamp=as_of,
                source=self.name,
                ingested_at=as_of,
                option_id="PETRJ320",
                bid=0.8,
                ask=1.0,
                last=0.9,
                mid=0.9,
                volume=900,
                open_interest=4500,
            ),
        ]


def test_live_provider_service_builds_deterministic_options_analysis():
    as_of = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    service = LiveProviderService(
        market_provider=FakeMarketProvider(),
        options_provider=FakeOptionsProvider(),
    )

    result = service.load("petr4", as_of=as_of)

    assert result.ticker == "PETR4"
    assert result.source_refs == ("brapi", "oplab")
    assert len(result.market_records) == 1
    assert len(result.option_contracts) == 2
    assert len(result.option_quotes) == 2
    assert len(result.options_analysis.puts) == 1
    assert len(result.options_analysis.calls) == 1
    assert result.options_analysis.calls[0].current_price == 29.0
    assert result.options_analysis.assumptions["live_provider_snapshot"] is True


def test_live_provider_fetches_oplab_chain_once(monkeypatch):
    as_of = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    calls = []
    payload = [{
        "symbol": "PETRJ320", "type": "CALL", "strike": 32.0,
        "due_date": "2026-10-16", "bid": 0.8, "ask": 1.0, "last": 0.9,
    }]
    adapter = OplabOptionsAdapter()
    monkeypatch.setattr(adapter, "_get_payload", lambda ticker: calls.append(ticker) or payload)
    result = LiveProviderService(
        market_provider=FakeMarketProvider(), options_provider=adapter
    ).load("PETR4", as_of=as_of)
    assert calls == ["PETR4"]
    assert result.option_contracts[0].option_id == result.option_quotes[0].option_id
    assert len(result.options_analysis.calls) == 1
