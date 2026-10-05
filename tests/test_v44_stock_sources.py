from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import sqlite3
from urllib.request import Request

import pandas as pd
import pytest

from b3_agent.providers.brapi.budget import BrapiBudget, BrapiBudgetExceeded
from b3_agent.providers.http_retry import request_json
from b3_agent.providers.local_market_history import LocalFirstMarketDataAdapter
from b3_agent.providers.stock_sources import RecordCache, StockFundamentalsProvider, StockQuoteProvider
from b3_agent.providers.yahoo import YahooAdapter
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.fundamental import StockFundamental
from b3_agent.repositories.market_data import MarketDataRepository


def quote(source="yahoo", day=None):
    now = datetime.now(timezone.utc)
    return StockMarketData(instrument_id="PETR4", ticker="PETR4", observation_timestamp=day or now,
        available_timestamp=now, source=source, ingested_at=now,
        open=30, high=32, low=29, close=31, volume=100)


class Provider:
    def __init__(self, name, rows=None, error=False):
        self.name, self.rows, self.error, self.calls = name, rows or [], error, 0

    def _get(self):
        self.calls += 1
        if self.error:
            raise RuntimeError("unavailable")
        return self.rows

    def get_current_quote(self, ticker):
        return self._get()[0]

    def get_financial_data(self, ticker):
        return self._get()

    def get_market_data(self, ticker, start, end):
        return self._get()


def metric(name, value, source, unit="ratio"):
    now = datetime.now(timezone.utc)
    return StockFundamental(instrument_id="PETR4", ticker="PETR4", observation_timestamp=now,
        available_timestamp=now, source=source, ingested_at=now, metric=name, value=value, unit=unit)


def test_quota_fail_closed_and_atomic_across_instances(tmp_path, monkeypatch):
    path = tmp_path / "budget.sqlite3"
    monkeypatch.delenv("B3_BRAPI_LOCAL_ALLOWANCE")
    with pytest.raises(BrapiBudgetExceeded):
        BrapiBudget(path).reserve("https://brapi.dev/api/quote/PETR4?token=SECRET")
    monkeypatch.setenv("B3_BRAPI_LOCAL_ALLOWANCE", "7")
    def attempt(_):
        try:
            BrapiBudget(path).reserve("https://brapi.dev/api/quote/PETR4?token=SECRET")
            return True
        except BrapiBudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=12) as executor:
        assert sum(executor.map(attempt, range(40))) == 7
    assert BrapiBudget(path).snapshot()["local_attempts"] == 7
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 7
        assert all("SECRET" not in str(row) for row in connection.execute("SELECT * FROM attempts"))


def test_quota_uses_billing_timezone_and_reserve(tmp_path, monkeypatch):
    monkeypatch.setenv("B3_BRAPI_LOCAL_ALLOWANCE", "99999")
    monkeypatch.setenv("B3_BRAPI_BASELINE_USED", "14998")
    monkeypatch.setenv("B3_BRAPI_BASELINE_PERIOD", "2026-09-01")
    monkeypatch.setenv("B3_BRAPI_OPERATIONAL_RESERVE", "1")
    now = datetime(2026, 10, 1, 1, tzinfo=timezone.utc)  # Still September in Brazil.
    budget = BrapiBudget(tmp_path / "quota.sqlite3")
    assert budget.snapshot(now=now)["period"] == "2026-09-01"
    budget.reserve("https://brapi.dev/api/quote/PETR4", now=now)
    with pytest.raises(BrapiBudgetExceeded):
        budget.reserve("https://brapi.dev/api/quote/PETR4", now=now)
    assert budget.snapshot(now=now+timedelta(days=1))["local_attempts"] == 0


def test_retry_reserves_each_http_attempt(monkeypatch):
    monkeypatch.setenv("B3_BRAPI_LOCAL_ALLOWANCE", "2")
    monkeypatch.setenv("B3_PROVIDER_RETRY_DELAY_SECONDS", "0")
    calls = []
    def opener(*args, **kwargs):
        calls.append(1)
        raise TimeoutError()
    with pytest.raises(BrapiBudgetExceeded):
        request_json(Request("https://brapi.dev/api/quote/PETR4"), provider="brapi",
            timeout_env="unused_timeout", default_timeout=1, opener=opener)
    assert len(calls) == 2
    assert BrapiBudget().snapshot()["local_attempts"] == 2


def test_quote_yahoo_then_oplab_then_brapi_and_cache(tmp_path):
    yahoo = Provider("yahoo", error=True)
    oplab = Provider("oplab", [quote("oplab")])
    brapi = Provider("brapi", [quote("brapi")])
    service = StockQuoteProvider(yahoo=yahoo, oplab=oplab, brapi=brapi, cache=RecordCache(tmp_path))
    assert service.get_current_quote("PETR4").source == "oplab"
    assert service.get_current_quote("PETR4").source == "oplab"
    assert yahoo.calls == oplab.calls == 1 and brapi.calls == 0
    assert service.last_reuse_telemetry["cache_reused"] is True


def test_fundamental_fallback_by_field_preserves_yahoo_and_cache(tmp_path):
    yahoo = Provider("yahoo", [metric("priceEarnings", 5, "yahoo"), metric("returnOnEquity", .2, "yahoo", "fraction")])
    brapi = Provider("brapi", [metric("priceEarnings", 99, "brapi"), metric("priceToBook", 1.2, "brapi")])
    service = StockFundamentalsProvider(yahoo=yahoo, brapi=brapi, cache=RecordCache(tmp_path))
    rows = {r.metric:r for r in service.get_financial_data("PETR4")}
    assert rows["priceEarnings"].source == "yahoo" and rows["priceEarnings"].value == 5
    assert rows["priceToBook"].source == "brapi"
    service.get_financial_data("PETR4")
    assert yahoo.calls == brapi.calls == 1
    assert any(d["source"] == "oplab" and d["status"] == "UNSUPPORTED" for d in service.diagnostics)


def test_cache_windows_do_not_accumulate_files_or_reuse_wrong_range(tmp_path):
    cache = RecordCache(tmp_path)
    first = ["dividends-v1", "yahoo", "PETR4", "2025-01-01", "2026-01-01"]
    second = ["dividends-v1", "yahoo", "PETR4", "2025-01-02", "2026-01-02"]
    cache.get_or_fetch(first, StockMarketData, 86400, lambda: [quote()])
    assert cache.peek(second, StockMarketData, 86400) == []
    cache.get_or_fetch(second, StockMarketData, 86400, lambda: [quote()])
    assert len(list(tmp_path.glob("*.json"))) == 1
    assert cache.peek(first, StockMarketData, 86400) == []


def test_nonfinite_fundamental_is_not_admitted(tmp_path):
    yahoo = Provider("yahoo", [metric("priceEarnings", 5, "yahoo"), metric("returnOnEquity", float("nan"), "yahoo", "fraction")])
    brapi = Provider("brapi", error=True)
    rows = StockFundamentalsProvider(yahoo=yahoo, brapi=brapi, cache=RecordCache(tmp_path)).get_financial_data("PETR4")
    assert [row.metric for row in rows] == ["priceEarnings"]


def test_history_local_authority_then_yahoo(tmp_path):
    day = datetime(2026, 9, 25, 21, tzinfo=timezone.utc)
    archived = quote("b3_cotahist", day)
    MarketDataRepository(tmp_path / "archive").write([archived])
    yahoo = Provider("yahoo", [quote("yahoo", day), quote("yahoo", day+timedelta(days=3))])
    oplab = Provider("oplab", error=True)
    brapi = Provider("brapi", error=True)
    service = LocalFirstMarketDataAdapter(tmp_path/"archive", tmp_path/"brapi", brapi_provider=brapi,
        oplab_provider=oplab, yahoo_provider=yahoo)
    rows = service.get_market_data("PETR4", date(2026, 9, 25), date(2026, 9, 28))
    assert [r.source for r in rows] == ["b3_cotahist", "yahoo"]
    assert rows[0] == archived and oplab.calls == brapi.calls == 0


def test_incompatible_yahoo_overlap_falls_back_without_overwriting_archive(tmp_path):
    day = datetime(2026, 9, 25, 21, tzinfo=timezone.utc)
    archived = quote("b3_cotahist", day)
    MarketDataRepository(tmp_path/"archive").write([archived])
    yahoo = Provider("yahoo", [replace(quote("yahoo", day), close=20), quote("yahoo", day+timedelta(days=3))])
    oplab = Provider("oplab", [quote("oplab", day+timedelta(days=3))])
    brapi = Provider("brapi", error=True)
    service = LocalFirstMarketDataAdapter(tmp_path/"archive", tmp_path/"brapi", brapi_provider=brapi,
        oplab_provider=oplab, yahoo_provider=yahoo)
    rows = service.get_market_data("PETR4", date(2026,9,25), date(2026,9,28))
    assert [row.source for row in rows] == ["b3_cotahist", "oplab"]
    assert rows[0] == archived and brapi.calls == 0


class FakeTicker:
    def __init__(self):
        self.args = None
    def history(self, **kwargs):
        self.args = kwargs
        return pd.DataFrame({"Open":[30], "High":[32], "Low":[29], "Close":[31], "Volume":[100], "Adj Close":[28], "Dividends":[.5]},
            index=pd.DatetimeIndex(["2026-09-25"], tz="America/Sao_Paulo"))
    def get_history_metadata(self):
        return {"currency":"BRL", "symbol":"PETR4.SA"}
    def get_info(self):
        return {"symbol":"PETR4.SA", "financialCurrency":"BRL", "debtToEquity":78.828,
                "revenueGrowth":-.09, "returnOnEquity":.2, "priceToBook":1.2}


def test_yahoo_explicit_adjustments_exclusive_end_units_and_dividend_dates():
    client = FakeTicker()
    service = YahooAdapter(lambda symbol: client)
    row = service.get_market_data("PETR4", date(2026,9,25), date(2026,9,25))[0]
    assert client.args["end"] == "2026-09-26"
    assert client.args["auto_adjust"] is False and client.args["repair"] is False
    assert row.close == 31 and row.adjusted_close == 28
    assert row.source == "yahoo" and row.observation_timestamp.hour == 3
    metrics = {r.metric:r for r in service.get_financial_data("PETR4")}
    assert metrics["debtToEquity"].unit == "percent"
    assert metrics["revenueGrowth"].unit == metrics["returnOnEquity"].unit == "fraction"
    assert metrics["priceToBook"].unit == "ratio"
    dividend = service.get_dividends("PETR4", start=date(2026,9,25), end=date(2026,9,25))[0]
    assert dividend.ex_date == date(2026,9,25) and dividend.payment_date is None
    assert dividend.payment_type == "UNKNOWN"


def test_yahoo_rejects_other_symbol_and_non_brl():
    client = FakeTicker()
    client.get_history_metadata = lambda: {"currency":"USD", "symbol":"PETR4.SA"}
    with pytest.raises(ValueError, match="currency"):
        YahooAdapter(lambda symbol: client).get_market_data("PETR4", date(2026,9,25), date(2026,9,25))
