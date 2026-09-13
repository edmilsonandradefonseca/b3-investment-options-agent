from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    ticker: str
    name: str
    asset_type: str
    exchange: str
    currency: str
    sector: str | None = None
    industry: str | None = None
    active_from: date | None = None
    active_to: date | None = None
