from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    ticker: str
    name: str
    asset_type: str
    exchange: str
    currency: str
    underlying_id: str | None = None
    sector: str | None = None
    industry: str | None = None
    active: bool = True
    active_from: date | None = None
    active_to: date | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
