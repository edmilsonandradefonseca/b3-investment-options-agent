from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from b3_agent.config import settings
from b3_agent.providers.bcb_sgs import BcbSgsAdapter
from b3_agent.repositories.macro import MacroDataRepository


@dataclass(frozen=True)
class MacroRefreshResult:
    start: date
    end: date
    fetched: int
    inserted: int
    duplicates: int
    latest_values: dict[str, float]


class MacroRefreshJob:
    """Fetch recent BCB macro observations and persist them idempotently."""

    INDICATORS = ("SELIC", "CDI", "IPCA")

    def __init__(
        self,
        *,
        adapter: BcbSgsAdapter | None = None,
        repository: MacroDataRepository | None = None,
        lookback_days: int = 120,
    ) -> None:
        if lookback_days < 1:
            raise ValueError("lookback_days must be positive")
        self.adapter = adapter or BcbSgsAdapter()
        self.repository = repository or MacroDataRepository(
            settings.data_dir / "normalized" / "macro"
        )
        self.lookback_days = lookback_days

    def run(self, *, as_of: date | None = None) -> MacroRefreshResult:
        end = as_of or date.today()
        start = end - timedelta(days=self.lookback_days)
        fetched_records = []

        for indicator in self.INDICATORS:
            fetched_records.extend(
                self.adapter.get_series(
                    indicator,
                    start=start,
                    end=end,
                )
            )

        inserted, duplicates = self.repository.upsert(fetched_records)
        latest_values = {}
        for indicator in self.INDICATORS:
            item = self.repository.latest(indicator)
            if item is not None:
                latest_values[indicator] = item.value

        return MacroRefreshResult(
            start=start,
            end=end,
            fetched=len(fetched_records),
            inserted=inserted,
            duplicates=duplicates,
            latest_values=latest_values,
        )


def local_today() -> date:
    from datetime import datetime

    return datetime.now(ZoneInfo(settings.timezone)).date()
