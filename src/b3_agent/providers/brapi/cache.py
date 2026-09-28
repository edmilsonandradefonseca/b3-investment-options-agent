"""Small persistent daily-price cache for live analyses."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import fcntl

from b3_agent.providers.brapi.adapter import BrapiAdapter
from b3_agent.repositories.market_data import MarketDataRepository
from b3_agent.schemas.market import StockMarketData


class CachedBrapiAdapter:
    name = "brapi"

    def __init__(
        self,
        cache_dir: Path,
        provider: BrapiAdapter | None = None,
        refresh_after: timedelta = timedelta(minutes=30),
    ) -> None:
        self.repository = MarketDataRepository(cache_dir)
        self.provider = provider or BrapiAdapter()
        self.refresh_after = refresh_after

    def get_market_data(self, ticker: str, start: date, end: date) -> list[StockMarketData]:
        ticker = ticker.upper().strip()
        if not ticker or start > end:
            raise ValueError("invalid ticker or date range")
        cache_path = self.repository.root_path / f"ticker={ticker}" / "market.parquet"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = cache_path.with_suffix(".lock")
        with lock_path.open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            cached = self.repository.read(ticker)
            now = datetime.now(timezone.utc)
            fresh = cache_path.exists() and (
                now.timestamp() - cache_path.stat().st_mtime < self.refresh_after.total_seconds()
            )
            # An initial load covers the requested interval. Later refreshes
            # overlap recent days to capture provider corrections.
            covers_start = bool(cached) and min(
                r.observation_timestamp.date() for r in cached
            ) <= start + timedelta(days=4)
            if not cached or not covers_start:
                fetched = self.provider.get_market_data(ticker, start, end)
            elif not fresh:
                latest = max(r.observation_timestamp.date() for r in cached)
                fetched = self.provider.get_market_data(
                    ticker, max(start, latest - timedelta(days=5)), end
                )
            else:
                fetched = []
            if fetched:
                by_date = {
                    r.observation_timestamp.date(): r
                    for r in cached
                    if r.observation_timestamp.date() >= start - timedelta(days=5)
                }
                by_date.update({r.observation_timestamp.date(): r for r in fetched})
                self.repository.write([by_date[d] for d in sorted(by_date)])
                cached = list(by_date.values())
            return sorted(
                (r for r in cached if start <= r.observation_timestamp.date() <= end),
                key=lambda r: r.observation_timestamp,
            )
