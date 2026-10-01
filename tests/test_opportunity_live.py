from __future__ import annotations

from datetime import date, datetime, timezone

from b3_agent.opportunity_live import (
    CANDIDATE_ORDER_POLICY,
    LiveOpportunityService,
    MARKETABILITY_POLICY,
)
from b3_agent.options.analysis import OptionsAnalysis
from b3_agent.orchestration.live_providers import LiveProviderSnapshot
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.option import OptionContract, OptionQuote
from b3_agent.schemas.position import PortfolioContext, Position


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
            OptionContract(
                option_id="WEGEJ550",
                underlying_id="WEGE3",
                underlying_ticker="WEGE3",
                option_ticker="WEGEJ550",
                option_type="CALL",
                strike=55.0,
                expiration_date=date(2026, 11, 20),
                contract_multiplier=100.0,
            ),
        )
        quotes = (
            _quote("WEGEV500", bid=1.20, ask=1.40, volume=1500),
            _quote("WEGEV520", bid=None, ask=0.10, volume=2000),
            _quote("WEGEJ550", bid=0.80, ask=0.90, volume=900),
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
    assert MARKETABILITY_POLICY in result.opportunity_set.ranking_policy_version
    assert result.opportunity_set.ranking_policy_version.endswith(
        CANDIDATE_ORDER_POLICY
    )
    assert result.ranking_status == "DEFERRED_INCOMPLETE_CONTEXT"
    assert "Annualized return remains evidence only" in result.ranking_reason
    assert result.option_marketability["WEGEV500"]["eligible"] is True
    assert "WEGEV520" not in result.option_marketability
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
    assert payload["opportunity_ranking_status"] == "DEFERRED_INCOMPLETE_CONTEXT"


def test_live_opportunity_service_includes_only_covered_calls():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 27),
        positions=(
            Position(
                position_id="WEGE3-STOCK",
                ticker="WEGE3",
                instrument_type="STOCK",
                quantity=100.0,
                market_price=49.6,
                market_value=4960.0,
            ),
        ),
        cash=0.0,
        cash_is_known=False,
        source_refs=("BTG",),
    )

    result = LiveOpportunityService(
        live_provider=FakeLiveProvider(),
    ).build("WEGE3", as_of=AS_OF, portfolio=portfolio)

    actions = {
        item.opportunity_id: item.action
        for item in result.opportunity_set.ranked_opportunities
    }
    assert actions["SELL_PUT:WEGEV500"] == "SELL_PUT"
    assert actions["SELL_CALL:WEGEJ550"] == "SELL_CALL"
    call_market = result.option_marketability["WEGEJ550"]
    assert call_market["covered_call"] is True
    assert call_market["stock_shares_available"] == 100.0
    assert call_market["covered_shares_required"] == 100.0
    assert call_market["premium_yield"] > 0
    assert call_market["annualized_return"] > 0


def test_live_opportunity_service_excludes_uncovered_calls():
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 27),
        positions=(
            Position(
                position_id="WEGE3-STOCK",
                ticker="WEGE3",
                instrument_type="STOCK",
                quantity=50.0,
                market_price=49.6,
                market_value=2480.0,
            ),
        ),
        cash=0.0,
        cash_is_known=False,
        source_refs=("BTG",),
    )

    result = LiveOpportunityService(
        live_provider=FakeLiveProvider(),
    ).build("WEGE3", as_of=AS_OF, portfolio=portfolio)

    ids = {
        item.opportunity_id
        for item in result.opportunity_set.ranked_opportunities
    }
    assert "SELL_CALL:WEGEJ550" not in ids
    assert "WEGEJ550" not in result.option_marketability
