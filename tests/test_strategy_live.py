from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from b3_agent.schemas.fundamental import StockFundamental
from b3_agent.schemas.market import StockMarketData
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
    assert result["asset_evidence"]["VALE3"]["fundamentals"]["metric_count"] == 1
    assert result["asset_evidence"]["VALE3"]["portfolio"]["held"] is False
    assert result["strategy_comparison"]["alternatives"][0]["capital_required"] == 50_000.0
    assert result["strategy_comparison"]["alternatives"][1]["capital_required"] == 50_000.0
    assert result["strategy_comparison"]["assumptions"]["ranking"] == "not_applied"
    assert result["quality_status"] == "WARNING"
    assert "PETR4" not in str(result["asset_evidence"])


def test_strategy_service_rejects_unsupported_sell_put_until_builder_exists():
    evidence = StrategyEvidenceService(
        market_provider=FakeMarketProvider(),
        fundamentals_provider=FakeFundamentalsProvider(),
    )
    service = LiveStrategyComparisonService(evidence_service=evidence)

    try:
        service.compare(
            assets=("VALE3", "WEGE3"),
            strategies=("Comprar ação", "Vender PUT"),
            portfolio=_portfolio(),
            as_of=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "supports BUY_STOCK and HOLD" in str(exc)
    else:
        raise AssertionError("unsupported strategy must not be silently inferred")
