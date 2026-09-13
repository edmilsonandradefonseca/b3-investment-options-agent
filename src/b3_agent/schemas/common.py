from dataclasses import dataclass
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
        return {
            "instrument_id": self.instrument_id,
            "ticker": self.ticker,
            "observation_timestamp": self.observation_timestamp.isoformat(),
            "available_timestamp": self.available_timestamp.isoformat(),
            "source": self.source,
            "ingested_at": self.ingested_at.isoformat(),
            "schema_version": self.schema_version,
            "source_record_id": self.source_record_id,
            "quality_status": self.quality_status,
            "quality_flags": self.quality_flags,
        }
