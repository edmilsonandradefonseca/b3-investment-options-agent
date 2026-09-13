from dataclasses import dataclass
from datetime import date, datetime

from .common import DataRecord


@dataclass(frozen=True)
class OptionContract:
    option_id: str
    underlying_id: str
    underlying_ticker: str
    option_ticker: str
    option_type: str
    strike: float
    expiration_date: date
    exercise_style: str | None = None
    contract_multiplier: float = 1.0
    currency: str = "BRL"


@dataclass(frozen=True)
class OptionQuote(DataRecord):
    option_id: str
    bid: float | None
    ask: float | None
    last: float | None
    mid: float | None
    volume: float
    open_interest: float | None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


