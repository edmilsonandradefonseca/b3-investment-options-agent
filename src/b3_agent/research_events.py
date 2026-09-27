from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from collections.abc import Iterable
from b3_agent.schemas.news import NewsEvidence

@dataclass(frozen=True)
class ResearchEvent:
    event_id: str
    ticker: str
    event_type: str
    published_at: datetime
    available_at: datetime
    headline: str
    summary: str | None
    source_name: str
    source_ref: str
    relevance: str | None = None

@dataclass(frozen=True)
class ResearchSnapshot:
    as_of: datetime
    events: tuple[ResearchEvent, ...]
    excluded_future_count: int
    source_refs: tuple[str, ...]

class ResearchEventService:
    """UC-10 PIT-safe normalization; collection remains provider-owned."""
    def build(self, records: Iterable[NewsEvidence], *, as_of: datetime) -> ResearchSnapshot:
        if as_of.tzinfo is None: raise ValueError("as_of must be timezone-aware")
        events=[]; future=0
        for item in records:
            available=_aware(item.available_timestamp)
            observed=_aware(item.observation_timestamp)
            if available > as_of or observed > as_of:
                future += 1; continue
            published=datetime.combine(item.published_date,datetime.min.time(),tzinfo=timezone.utc) if item.published_date else observed
            source_ref=item.url or item.source_record_id or f"{item.source}:{item.ticker}:{published.isoformat()}"
            events.append(ResearchEvent(source_ref,item.ticker,item.event_type or "NEWS",published,available,item.headline,item.summary,item.source_name,source_ref,item.relevance))
        events.sort(key=lambda x:(x.published_at,x.event_id),reverse=True)
        return ResearchSnapshot(as_of,tuple(events),future,tuple(dict.fromkeys(e.source_ref for e in events)))

def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
