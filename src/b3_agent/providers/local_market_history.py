"""Merge validated local history with Yahoo/OPLAB/BRAPI for uncovered dates."""

from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.providers.brapi.cache import CachedBrapiAdapter
from b3_agent.providers.http_retry import ProviderRequestError
from b3_agent.providers.brapi.budget import fallback_reason
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


class MarketHistoryProvider(Protocol):
    def get_market_data(
        self, ticker: str, start: date, end: date
    ) -> list[StockMarketData]: ...


class LocalFirstMarketDataAdapter:
    """Read COTAHIST locally and fill uncovered dates from live providers.

    Source precedence is intentionally deterministic:

    1. existing local validated archive for persisted dates;
    2. Yahoo for uncovered dates when configured;
    3. OPLAB historical data;
    4. cached BRAPI as the final remote fallback.

    Local observations are never overwritten by remote providers.
    """

    name = "local_b3_with_brapi_updates"

    def __init__(
        self,
        archive_dir: Path,
        brapi_cache_dir: Path,
        brapi_provider: BrapiAdapter | None = None,
        oplab_provider: MarketHistoryProvider | None = None,
        yahoo_provider: MarketHistoryProvider | None = None,
    ) -> None:
        self.archive = MarketDataRepository(archive_dir)
        self.yahoo = (CachedBrapiAdapter(brapi_cache_dir.parent / "yahoo_daily", provider=yahoo_provider)
                      if yahoo_provider is not None else None)
        self.oplab = oplab_provider
        self.brapi = CachedBrapiAdapter(brapi_cache_dir, provider=brapi_provider)

    def get_market_data(
        self, ticker: str, start: date, end: date
    ) -> list[StockMarketData]:
        normalized = ticker.upper().strip()
        if not normalized or start > end:
            raise ValueError("invalid ticker or date range")

        archived = {
            _market_date(record): record
            for record in self.archive.read(normalized)
            if start <= _market_date(record) <= end
        }
        if not archived:
            return self._remote_market_data(normalized, start, end)

        local_dates = sorted(archived)
        first_local = local_dates[0]
        last_local = local_dates[-1]
        combined = dict(archived)

        # If the archive starts materially after the requested window, use the
        # live provider chain to fill the earlier range.
        if (first_local - start).days > 4:
            self._merge_remote(
                combined,
                normalized,
                start,
                first_local - timedelta(days=1),
            )

        # Request the uncovered tail for every calendar day. Providers return
        # only published exchange sessions, so weekend requests still recover
        # the latest completed weekday candle after a stale local archive.
        if last_local < end:
            self._merge_remote(
                combined,
                normalized,
                last_local + timedelta(days=1),
                end,
            )

        return [combined[day] for day in sorted(combined)]

    def _remote_market_data(
        self,
        ticker: str,
        start: date,
        end: date,
        anchor: StockMarketData | None = None,
    ) -> list[StockMarketData]:
        failures = []
        for label, provider in (("yahoo", self.yahoo), ("oplab", self.oplab), ("brapi", self.brapi)):
            if provider is None:
                continue
            try:
                with fallback_reason("daily_history; " + "; ".join(failures)):
                    if label == "yahoo" and anchor is not None:
                        anchor_day = _market_date(anchor)
                        candidate = provider.get_market_data(ticker, min(start, anchor_day), max(end, anchor_day))
                        overlap = next((row for row in candidate if _market_date(row) == anchor_day), None)
                        if overlap is None or any(abs(getattr(overlap, field)/getattr(anchor, field)-1) > .005
                            for field in ("open", "high", "low", "close") if getattr(anchor, field) > 0):
                            raise ValueError("Yahoo overlap incompatible with retained local price basis")
                        rows = [row for row in candidate if start <= _market_date(row) <= end]
                    else:
                        rows = provider.get_market_data(ticker, start, end)
                if rows:
                    if any(r.ticker != ticker or r.currency != "BRL" for r in rows):
                        raise ValueError("history identity or currency mismatch")
                    if max(_market_date(r) for r in rows) < end - timedelta(days=4):
                        raise ValueError("history does not cover requested tail")
                    return rows
                failures.append(f"{label}:EMPTY")
            except (OSError, RuntimeError, ValueError, ProviderRequestError) as exc:
                failures.append(f"{label}:{type(exc).__name__}")
        raise RuntimeError("market history unavailable for " + ticker + ": " + "; ".join(failures))

    def _merge_remote(
        self,
        combined: dict[date, StockMarketData],
        ticker: str,
        start: date,
        end: date,
    ) -> None:
        if start > end:
            return
        try:
            prior = [record for day, record in combined.items() if day < start]
            later = [record for day, record in combined.items() if day > end]
            anchor = (max(prior, key=_market_date) if prior else min(later, key=_market_date) if later else None)
            remote = self._remote_market_data(ticker, start, end, anchor=anchor)
        except (OSError, RuntimeError, ValueError, ProviderRequestError):
            # Preserve usable offline/local history during provider outages or
            # before the first quote of a new session is published.
            return
        for record in remote:
            day = _market_date(record)
            if start <= day <= end:
                combined.setdefault(day, record)


def _market_date(record: StockMarketData) -> date:
    """Use the exchange date encoded by COTAHIST when available."""
    if record.source == "b3_cotahist" and record.source_record_id:
        parts = record.source_record_id.split(":", 2)
        if len(parts) == 3:
            try:
                return date.fromisoformat(parts[1])
            except ValueError:
                pass
    return record.observation_timestamp.date()
