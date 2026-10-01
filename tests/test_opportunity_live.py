from __future__ import annotations

from datetime import date, datetime, timezone

from b3_agent.opportunity_live import (
    LiveOpportunityService,
    MARKETABILITY_POLICY,
)
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.orchestration.live_providers import LiveProviderSnapshot
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.option import OptionContract, OptionQuote


AS_OF = datetime(2026, 10, 1, 17, 0, tzinfo=timezone.utc)


def _market() -> StockMarketData:
    return StockMarketData(
        instrument_id="WEGE3",
        ticker="WEGE3",
        observation_timestamp=AS_OF,
        available_timestamp=AS_OF,
        source="oplab",
        ingested_at=AS_OF,
        source_record_id="WEGE3:current",
        quality_flags=("current_quote",),
        open=49.0,
        high=50.0,
        low=48.5,
        close=49.6,
        volume=2_000_000,
        currency="BRL",
    )


def _contract(option_id: str, strike: float) -> OptionContract:
    return OptionContract(
        option_id=option_id,
        underlying_id="WEGE3",
        underlying_ticker="WEGE3",
        option_ticker=option_id,
        option_type="PUT",
        strike=strike,
        expiration_date=date(2026, 11, 20),
        contract_multiplier=100.0,
    )


def _quote(
    option_id: str,
    *,
    bid: float | None,
    ask: float | None,
    volume: float,
) -> OptionQuote:
    return OptionQuote(
        instrument_id=option_id,
        ticker="WEGE3",
        observation_timestamp=AS_OF,
        available_timestamp=AS_OF,
        source="oplab",
        ingested_at=AS_OF,
        source_record_id=f"WEGE3:{option_id}:current",
        option_id=option_id,
        bid=bid,
        ask=ask,
        last=bid,
        mid=((bid + ask) / 2.0 if bid is not None and ask is not None else None),
        volume=volume,
        open_interest=1000,
    )


class FakeLiveProvider:
    def load(self, ticker: str, *, as_of=None):
        assert ticker == "WEGE3"
        effective = as_of or AS_OF
        current = _market()
        contracts = (
            _contract("WEGEV500", 50.0),
            _contract("WEGEV520", 52.0),
        )
        quotes = (
            _quote("WEGEV500", bid=1.20, ask=1.40, volume=1500),
            _quote("WEGEV520", bid=None, ask=0.10, volume=2000),
        )
        return LiveProviderSnapshot(
            ticker="WEGE3",
            as_of=effective,
            market_records=(current,),
            current_stock_quote=current,
            option_contracts=contracts,
            option_quotes=quotes,
            options_analysis=OptionsAnalysis(source_refs=("oplab",)),
            source_refs=("oplab",),
        )


def test_live_opportunity_service_builds_only_executable_sell_puts():
    result = LiveOpportunityService(
        live_provider=FakeLiveProvider(),
    ).build("WEGE3", as_of=AS_OF)

    ranked = result.opportunity_set.ranked_opportunities
    assert len(ranked) == 1
    assert ranked[0].opportunity_id == "SELL_PUT:WEGEV500"
    assert ranked[0].action == "SELL_PUT"
    assert ranked[0].capital_requirement == 5000.0
    assert ranked[0].expected_return is not None
    assert result.opportunity_set.ranking_policy_version.endswith(
        MARKETABILITY_POLICY
    )
    assert result.option_marketability["WEGEV500"]["eligible"] is True
    assert result.option_marketability["WEGEV520"]["eligible"] is False
    assert any(
        "Stock BUY/ACCUMULATE opportunities are not ranked" in item
        for item in result.limitations
    )


def test_live_opportunity_payload_is_frontend_safe():
    service = LiveOpportunityService(live_provider=FakeLiveProvider())
    payload = service.as_payload(service.build("WEGE3", as_of=AS_OF))

    assert payload["ticker"] == "WEGE3"
    assert payload["opportunity_set"]["ranked_opportunities"][0][
        "opportunity_id"
    ] == "SELL_PUT:WEGEV500"
    assert payload["option_marketability"]["WEGEV500"]["source"] == "oplab"
