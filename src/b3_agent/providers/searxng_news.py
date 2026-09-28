from __future__ import annotations

from datetime import date, datetime, timezone
import json
import urllib.parse
import urllib.request
from urllib.parse import urlparse

from b3_agent.schemas.news import NewsEvidence


class SearxngNewsAdapter:
    """Acquire web/news evidence through the shared local SearXNG service."""

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8080",
        timeout: float = 20.0,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "searxng"

    def search(
        self,
        ticker: str,
        *,
        query: str | None = None,
        limit: int = 20,
    ) -> tuple[NewsEvidence, ...]:
        normalized = ticker.upper().strip()
        if not normalized:
            raise ValueError("ticker must not be empty")
        if limit < 1:
            raise ValueError("limit must be positive")

        q = query.strip() if query and query.strip() else f"{normalized} B3 mercado"
        params = urllib.parse.urlencode(
            {
                "q": q,
                "format": "json",
                "language": "pt-BR",
                "safesearch": 1,
                "categories": "news",
                "time_range": "day",
            }
        )
        request = urllib.request.Request(
            f"{self.base_url}/search?{params}",
            headers={
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = payload.get("results", ())
        if not isinstance(results, list):
            raise ValueError("SearXNG returned an invalid results payload")

        ingested_at = datetime.now(timezone.utc)
        output: list[NewsEvidence] = []
        for index, item in enumerate(results[:limit]):
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue

            published_date = _published_date(
                item.get("publishedDate")
                or item.get("published_date")
                or item.get("pubdate")
            )
            observation_timestamp = (
                datetime.combine(
                    published_date,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                )
                if published_date is not None
                else ingested_at
            )
            engine = item.get("engine")
            engines = item.get("engines")
            source_name = (
                str(engine)
                if engine
                else str(engines[0])
                if isinstance(engines, list) and engines
                else (urlparse(url).netloc or "web")
            )

            output.append(
                NewsEvidence(
                    instrument_id=normalized,
                    ticker=normalized,
                    observation_timestamp=observation_timestamp,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=f"{normalized}:{index}:{url}",
                    headline=title,
                    source_name=source_name,
                    url=url,
                    published_date=published_date,
                    event_type="NEWS",
                    summary=str(item.get("content") or "").strip() or None,
                    relevance=None,
                )
            )

        return tuple(output)


def _published_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
