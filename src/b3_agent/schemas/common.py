from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, kw_only=True)
class DataRecord:
    instrument_id: str
    ticker: str
    observation_timestamp: datetime
    available_timestamp: datetime
    source: str
    ingested_at: datetime
    schema_version: str = "1.0"
    source_record_id: str | None = None
    quality_status: str = "VALID"
    quality_flags: tuple[str, ...] = ()

    def is_available_at(self, decision_timestamp: datetime) -> bool:
        """Return whether this record was available at a decision time.

        Provider adapters may return timezone-aware timestamps while legacy
        fixtures can contain naive timestamps. For point-in-time comparison,
        naive timestamps are interpreted as UTC so mixed provider/test data
        cannot raise a naive-vs-aware comparison error.
        """
        available = self.available_timestamp
        decision = decision_timestamp
        if available.tzinfo is None:
            available = available.replace(tzinfo=timezone.utc)
        if decision.tzinfo is None:
            decision = decision.replace(tzinfo=timezone.utc)
        return available <= decision

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete dataclass, including subclass fields."""
        data = asdict(self)

        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        return data
