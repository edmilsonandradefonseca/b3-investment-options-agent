"""Merge the local B3 archive with OPLAB/BRAPI for uncovered dates."""

from datetime import date, timedelta
from pathlib import Path
from typing import Protocol

from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.providers.brapi.cache import CachedBrapiAdapter
from b3_agent.providers.http_retry import ProviderRequestError
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


class MarketHistoryProvider(Protocol):
    def get_market_data(
        self, ticker: str, start: date, end: date
    ) -> list[StockMarketData]: ...


class LocalFirstMarketDataAdapter:
    """Read COTAHIST locally and fill uncovered dates from live providers.

    Source precedence is intentionally deterministic:

    1. local B3 COTAHIST archive for dates already persisted;
    2. OPLAB historical data for uncovered/live dates when configured;
    3. cached BRAPI as the final remote fallback.

    Local observations are never overwritten by remote providers.
    """

    name = "local_b3_with_brapi_updates"

    def __init__(
        self,
        archive_dir: Path,
        brapi_cache_dir: Path,
        brapi_provider: BrapiAdapter | None = None,
        oplab_provider: MarketHistoryProvider | None = None,
    ) -> None:
        self.archive = MarketDataRepository(archive_dir)
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

        # Fill dates after the local archive on weekdays. If the live provider
        # has not published a new daily candle yet, keep the last local close.
        if last_local < end and end.weekday() < 5:
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
    ) -> list[StockMarketData]:
        oplab_error: Exception | None = None
        if self.oplab is not None:
            try:
                rows = self.oplab.get_market_data(ticker, start, end)
            except (OSError, RuntimeError, ValueError, ProviderRequestError) as exc:
                oplab_error = exc
            else:
                if rows:
                    return rows

        try:
            return self.brapi.get_market_data(ticker, start, end)
        except (OSError, RuntimeError, ValueError, ProviderRequestError) as exc:
            if oplab_error is not None:
                raise RuntimeError(
                    f"market history unavailable for {ticker}: "
                    f"OPLAB={oplab_error}; BRAPI={exc}"
                ) from exc
            raise

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
            remote = self._remote_market_data(ticker, start, end)
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
