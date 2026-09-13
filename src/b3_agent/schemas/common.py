from dataclasses import asdict, dataclass
from datetime import datetime
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
        """Return whether this record was available at a decision time."""
        return self.available_timestamp <= decision_timestamp

    def to_dict(self) -> dict[str, Any]:
        """Serialize the complete dataclass, including subclass fields."""
        data = asdict(self)

        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        return data