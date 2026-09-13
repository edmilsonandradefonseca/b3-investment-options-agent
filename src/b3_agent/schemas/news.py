from dataclasses import dataclass
from datetime import date

from .common import DataRecord


@dataclass(frozen=True)
class NewsEvidence(DataRecord):
    headline: str
    source_name: str
    url: str | None = None
    published_date: date | None = None
    event_type: str | None = None
    summary: str | None = None
    relevance: str | None = None
