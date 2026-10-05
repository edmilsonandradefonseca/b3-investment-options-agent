"""Capability-specific stock acquisition. Options remain exclusively OPLAB.

Cache entries retain provider records and their original availability dates.
Failures are diagnostics, never a successful empty population.
"""
from dataclasses import asdict
from datetime import date, datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
from threading import local

from b3_agent.config import settings
from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.providers.brapi.budget import fallback_reason
from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter
from b3_agent.providers.oplab.adapter import OplabAdapter
from b3_agent.providers.yahoo import YahooAdapter
from b3_agent.schemas.market import StockMarketData
from b3_agent.schemas.fundamental import StockFundamental
from b3_agent.schemas.dividend import DividendRecord


class RecordCache:
    def __init__(self, root: Path | None = None):
        self.root = root or settings.data_dir / "cache" / "stock_sources_v44"

    def peek(self, key, record_type, ttl):
        digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
        try:
            payload = json.loads((self.root / f"{digest}.json").read_text())
            age = datetime.now(timezone.utc).timestamp()-payload["fetched_at"]
            if payload["key"] == key and 0 <= age < ttl:
                return [_decode(item, record_type) for item in payload["records"]]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return []

    def get_or_fetch(self, key, record_type, ttl, fetch):
        digest = hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
        path = self.root / f"{digest}.json"
        self.root.mkdir(parents=True, exist_ok=True)
        with path.with_suffix(".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                payload = json.loads(path.read_text())
                age = datetime.now(timezone.utc).timestamp() - payload["fetched_at"]
                if payload["key"] == key and 0 <= age < ttl:
                    return [_decode(item, record_type) for item in payload["records"]], True
            except (OSError, ValueError, KeyError, TypeError):
                pass
            records = fetch()
            if not records:
                return [], False
            payload = {"key": key, "fetched_at": datetime.now(timezone.utc).timestamp(), "records": [asdict(r) for r in records]}
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, default=lambda item: item.isoformat()))
            temporary.replace(path)
            return records, False


def _decode(item, record_type):
    values = dict(item)
    for key in ("observation_timestamp", "available_timestamp", "ingested_at"):
        values[key] = datetime.fromisoformat(values[key])
    for key in ("report_date", "period_start", "period_end", "announcement_date", "ex_date", "record_date", "payment_date"):
        if values.get(key):
            values[key] = date.fromisoformat(values[key])
    values["quality_flags"] = tuple(values.get("quality_flags", ()))
    return record_type(**values)


class StockQuoteProvider:
    name = "stock_source_policy_v44"

    def __init__(self, *, yahoo=None, oplab=None, brapi=None, cache=None):
        self.yahoo = yahoo or YahooAdapter()
        self.oplab = oplab or OplabAdapter()
        self.brapi = brapi or BrapiAdapter()
        self.cache = cache or RecordCache()
        self._acquisition = local()

    @property
    def last_reuse_telemetry(self):
        return getattr(self._acquisition, "telemetry", {})

    def get_current_quote(self, ticker):
        failures = []
        # Any admissible local quote wins before a remote Yahoo request, even
        # when the cached quote originated from a lower-priority provider.
        for provider in (self.yahoo, self.oplab, self.brapi):
            rows = self.cache.peek(["quote-v1", provider.name, ticker.upper()], StockMarketData, 5)
            if rows:
                row = rows[0]
                age = (datetime.now(timezone.utc)-row.observation_timestamp).total_seconds()
                if row.ticker == ticker.upper() and row.currency == "BRL" and row.close > 0 and age >= 0 and (provider.name != "yahoo" or age <= 1800):
                    self._acquisition.telemetry = {"source": row.source, "cache_reused": True, "ttl_seconds": 5}
                    return row
        for provider in (self.yahoo, self.oplab, self.brapi):
            try:
                with fallback_reason("current_quote; " + "; ".join(failures)):
                    rows, reused = self.cache.get_or_fetch(["quote-v1", provider.name, ticker.upper()], StockMarketData, 5,
                        lambda: [provider.get_current_quote(ticker)])
                row = rows[0]
                age = (datetime.now(timezone.utc)-row.observation_timestamp).total_seconds()
                if row.ticker != ticker.upper() or row.currency != "BRL" or row.close <= 0 or age < 0:
                    raise ValueError("invalid quote identity, currency, price or timestamp")
                if provider.name == "yahoo" and age > 1800:
                    raise ValueError("Yahoo cached quote stale")
                self._acquisition.telemetry = {"source": row.source, "cache_reused": reused, "fallbacks": failures, "ttl_seconds": 5}
                return row
            except (OSError, RuntimeError, ValueError) as exc:
                failures.append(f"{provider.name}:{type(exc).__name__}")
        self._acquisition.telemetry = {"status": "UNAVAILABLE", "fallbacks": failures}
        raise RuntimeError("stock quote unavailable: " + "; ".join(failures))


CORE_FUNDAMENTALS = frozenset({"marketCap", "priceEarnings", "priceToBook", "earningsPerShare", "totalRevenue", "ebitda", "totalDebt", "returnOnEquity"})


class StockFundamentalsProvider:
    name = "stock_source_policy_v44"

    def __init__(self, *, yahoo=None, brapi=None, cache=None):
        self.yahoo = yahoo or YahooAdapter()
        # No OPLAB financial-statement capability exists in the adapter.
        # Declare unsupported instead of spending a request on a wrong API.
        self.brapi = brapi or BrapiFundamentalsAdapter()
        self.cache = cache or RecordCache()
        self._acquisition = local()

    @property
    def diagnostics(self):
        return getattr(self._acquisition, "diagnostics", [])

    def get_financial_data(self, ticker):
        selected = {}
        diagnostics = []
        for provider in (self.yahoo, self.brapi):
            if provider is self.brapi:
                diagnostics.append({"source": "oplab", "capability": "fundamentals", "status": "UNSUPPORTED"})
                if CORE_FUNDAMENTALS <= selected.keys():
                    break
            try:
                with fallback_reason("fundamentals; missing=" + ",".join(sorted(CORE_FUNDAMENTALS-selected.keys())) + "; " + json.dumps(diagnostics)):
                    rows, reused = self.cache.get_or_fetch(["fundamentals-v1", provider.name, ticker.upper()], StockFundamental, 86400,
                        lambda: provider.get_financial_data(ticker))
                for row in rows:
                    if row.ticker != ticker.upper() or row.unit is None:
                        continue
                    selected.setdefault(row.metric, row)
                diagnostics.append({"source": provider.name, "status": "AVAILABLE" if rows else "EMPTY", "cache_reused": reused})
            except (OSError, RuntimeError, ValueError) as exc:
                diagnostics.append({"source": provider.name, "status": "UNAVAILABLE", "error_type": type(exc).__name__})
        self._acquisition.diagnostics = diagnostics
        if not selected:
            raise RuntimeError("stock fundamentals unavailable: " + json.dumps(diagnostics))
        return list(selected.values())

    def get_dividends(self, ticker, *, start=None, end=None):
        diagnostics = []
        for provider in (self.yahoo, self.brapi):
            if provider is self.brapi:
                diagnostics.append({"source": "oplab", "capability": "dividends", "status": "UNSUPPORTED"})
            try:
                with fallback_reason("dividends; " + json.dumps(diagnostics)):
                    rows, reused = self.cache.get_or_fetch(["dividends-v1", provider.name, ticker.upper(), str(start), str(end)], DividendRecord, 86400,
                        lambda: provider.get_dividends(ticker, start=start, end=end))
                if rows:
                    self._acquisition.diagnostics = diagnostics + [{"source": provider.name, "status": "AVAILABLE", "cache_reused": reused}]
                    return rows
                diagnostics.append({"source": provider.name, "status": "EMPTY_NOT_EXHAUSTIVE"})
            except (OSError, RuntimeError, ValueError) as exc:
                diagnostics.append({"source": provider.name, "status": "UNAVAILABLE", "error_type": type(exc).__name__})
        self._acquisition.diagnostics = diagnostics
        raise RuntimeError("stock dividends unavailable or unverified empty coverage: " + json.dumps(diagnostics))
