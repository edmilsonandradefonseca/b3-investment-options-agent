from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from b3_agent.schemas.fundamental import StockFundamental
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.option import OptionContract, OptionQuote
from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.strategy_live import LiveStrategyComparisonService, StrategyEvidenceService


class FakeMarketProvider:
    name = "fake-market"

    def get_market_data(self, ticker, start, end):
        observed = datetime(2026, 7, 1, tzinfo=timezone.utc)
        rows = []
        base = 50.0 if ticker == "VALE3" else 30.0
        for index in range(70):
            price = base + index * 0.2
            rows.append(
                StockMarketData(
                    instrument_id=ticker,
                    ticker=ticker,
                    observation_timestamp=observed + timedelta(days=index),
                    available_timestamp=observed + timedelta(days=index, hours=1),
                    source=self.name,
                    ingested_at=observed + timedelta(days=index, hours=1),
                    source_record_id=f"{ticker}:{index}",
                    open=price - 0.1,
                    high=price + 0.3,
                    low=price - 0.2,
                    close=price,
                    volume=1_000_000 + index,
                )
            )
        return rows


class FakeCurrentQuoteProvider:
    name = "oplab"

    def get_current_quote(self, ticker):
        ts = datetime(2026, 10, 1, 15, 59, tzinfo=timezone.utc)
        price = 69.74 if ticker == "VALE3" else 49.74
        return StockMarketData(
            instrument_id=ticker,
            ticker=ticker,
            observation_timestamp=ts,
            available_timestamp=ts,
            source=self.name,
            ingested_at=ts,
            source_record_id=f"{ticker}:current",
            quality_flags=("current_quote",),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=2_000_000,
        )


class FakeOptionsProvider:
    name = "oplab"

    def get_snapshot(self, ticker, as_of):
        contract = OptionContract(
            option_id="WEGEV500",
            underlying_id="WEGE3",
            underlying_ticker="WEGE3",
            option_ticker="WEGEV500",
            option_type="PUT",
            strike=50.0,
            expiration_date=date(2026, 11, 20),
            contract_multiplier=100.0,
        )
        quote = OptionQuote(
            instrument_id="WEGEV500",
            ticker="WEGE3",
            observation_timestamp=as_of,
            available_timestamp=as_of,
            source=self.name,
            ingested_at=as_of,
            source_record_id="WEGE3:WEGEV500:current",
            option_id="WEGEV500",
            bid=1.20,
            ask=1.40,
            last=1.30,
            mid=1.30,
            volume=1500,
            open_interest=3000,
        )
        return [contract], [quote]


class FakeFundamentalsProvider:
    name = "fake-fundamentals"

    def get_financial_data(self, ticker):
        ts = datetime(2026, 9, 30, tzinfo=timezone.utc)
        return [
            StockFundamental(
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=ts,
                available_timestamp=ts,
                source=self.name,
                ingested_at=ts,
                source_record_id=f"{ticker}:eps",
                quality_status="WARNING",
                quality_flags=("availability_is_ingestion_time",),
                metric="earningsPerShare",
                value=4.2 if ticker == "VALE3" else 1.8,
                report_date=date(2026, 9, 30),
                period_type="TTM",
                unit="BRL/share",
            )
        ]


def _portfolio():
    return PortfolioContext(
        as_of=date(2026, 9, 27),
        cash=0.0,
        cash_is_known=False,
        positions=(
            Position(
                position_id="PETR4-STOCK",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=100,
                market_price=40.0,
                market_value=4000.0,
            ),
        ),
        source_refs=("BTG",),
    )


def test_live_strategy_comparison_builds_two_asset_evidence_packs_without_ranking():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
        history_days=120,
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)
    as_of = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)

    result = service.compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Comprar ação"),
        amount=50_000.0,
        portfolio=_portfolio(),
        as_of=as_of,
    )

    assert set(result["asset_evidence"]) == {"VALE3", "WEGE3"}
    assert result["asset_evidence"]["VALE3"]["market"]["history_count"] == 70
    assert result["asset_evidence"]["VALE3"]["market"]["current_quote"]["close"] == 69.74
    assert result["asset_evidence"]["WEGE3"]["market"]["current_quote"]["close"] == 49.74
    assert result["asset_evidence"]["VALE3"]["fundamentals"]["metric_count"] == 1
    assert result["asset_evidence"]["VALE3"]["portfolio"]["held"] is False
    assert result["strategy_comparison"]["alternatives"][0]["capital_required"] == 50_000.0
    assert result["strategy_comparison"]["alternatives"][1]["capital_required"] == 50_000.0
    assert result["strategy_comparison"]["assumptions"]["ranking"] == "not_applied"
    assert result["quality_status"] == "WARNING"
    assert "PETR4" not in str(result["asset_evidence"])


def test_sell_put_requires_explicit_contract():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )

    try:
        service.compare(
            assets=("VALE3", "WEGE3"),
            strategies=("Comprar ação", "Vender PUT"),
            portfolio=_portfolio(),
            as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "explicit current OPLAB option identifier" in str(exc)
    else:
        raise AssertionError("SELL_PUT must require an explicit contract")


def test_sell_put_uses_current_oplab_bid_and_one_cash_secured_contract():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
        current_quote_provider=FakeCurrentQuoteProvider(),
    )
    service = LiveStrategyComparisonService(
        evidence_service=evidence,
        options_provider=FakeOptionsProvider(),
    )
    as_of = datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc)

    result = service.compare(
        assets=("VALE3", "WEGE3"),
        strategies=("Comprar ação", "Vender PUT"),
        option_ids=(None, "WEGEV500"),
        amount=50_000.0,
        portfolio=_portfolio(),
        as_of=as_of,
    )

    alternative = result["strategy_comparison"]["alternatives"][1]
    assert alternative["action_type"] == "SELL_PUT"
    assert alternative["subject_id"] == "WEGEV500"
    assert alternative["capital_required"] == 5000.0
    assert alternative["max_loss"] == 4880.0
    assert alternative["assumptions"]["premium_basis"] == "current_bid"
    assert alternative["assumptions"]["current_option_quote"]["bid"] == 1.20
    assert result["option_evidence"]["WEGEV500"]["current_quote"]["last"] == 1.30
