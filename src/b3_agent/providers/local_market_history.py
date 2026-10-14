"""Merge the local B3 archive with BRAPI only for uncovered dates."""

from datetime import date, timedelta
from pathlib import Path

from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.providers.brapi.cache import CachedBrapiAdapter
from b3_agent.providers.http_retry import ProviderRequestError
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


class LocalFirstMarketDataAdapter:
    """Read COTAHIST locally and use the cached BRAPI adapter for date gaps.

    The local archive is authoritative on dates it contains. BRAPI fills dates
    outside the archive, including recent market updates. Weekend tail gaps are
    skipped because no B3 session can have occurred on those dates.
    """

    name = "local_b3_with_brapi_updates"

    def __init__(
        self,
        archive_dir: Path,
        brapi_cache_dir: Path,
        brapi_provider: BrapiAdapter | None = None,
    ) -> None:
        self.archive = MarketDataRepository(archive_dir)
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
            return self.brapi.get_market_data(normalized, start, end)

        local_dates = sorted(archived)
        first_local = local_dates[0]
        last_local = local_dates[-1]
        combined = dict(archived)

        # If the archive starts materially after the requested window, BRAPI
        # fills the earlier range. A short calendar gap can be a weekend/holiday.
        if (first_local - start).days > 4:
            self._merge_remote(combined, normalized, start, first_local - timedelta(days=1))

        # Ask BRAPI only for dates after the local archive, and only on weekdays.
        # If no new daily quote has been published yet, the last local close is
        # still returned with its original observation date.
        if last_local < end and end.weekday() < 5:
            self._merge_remote(combined, normalized, last_local + timedelta(days=1), end)

        return [combined[day] for day in sorted(combined)]

    def _merge_remote(
        self, combined: dict[date, StockMarketData], ticker: str, start: date, end: date
    ) -> None:
        if start > end:
            return
        try:
            remote = self.brapi.get_market_data(ticker, start, end)
        except (OSError, ValueError, ProviderRequestError):
            # Preserve usable offline history during a provider outage or before
            # the first quote of a new session is published.
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
