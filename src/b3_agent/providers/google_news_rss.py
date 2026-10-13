from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from b3_agent.schemas.news import NewsEvidence


_HTML_TAG = re.compile(r"<[^>]+>")


class GoogleNewsRssAdapter:
    """Zero-cost Google News RSS discovery fallback.

    This adapter is discovery-only. It does not confer authority on a headline;
    downstream UC-10 normalization/provenance rules remain unchanged.
    """

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, *, timeout: float = 15.0) -> None:
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "google_news_rss"

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

        q = query.strip() if query and query.strip() else f"{normalized} B3 mercado when:2d"
        params = urllib.parse.urlencode(
            {
                "q": q,
                "hl": "pt-BR",
                "gl": "BR",
                "ceid": "BR:pt-419",
            }
        )
        request = urllib.request.Request(
            f"{self.BASE_URL}?{params}",
            headers={
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/rss+xml, application/xml, text/xml",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read()

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError("Google News RSS returned invalid XML") from exc

        ingested_at = datetime.now(timezone.utc)
        output: list[NewsEvidence] = []
        for index, item in enumerate(root.findall("./channel/item")):
            if len(output) >= limit:
                break
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue

            pub_raw = (item.findtext("pubDate") or "").strip()
            published_at = _parse_pubdate(pub_raw)
            observed_at = published_at or ingested_at
            source_node = item.find("source")
            source_name = (
                (source_node.text or "").strip()
                if source_node is not None and source_node.text
                else "Google News"
            )
            description = _clean_html(item.findtext("description") or "")

            output.append(
                NewsEvidence(
                    instrument_id=normalized,
                    ticker=normalized,
                    observation_timestamp=observed_at,
                    available_timestamp=ingested_at,
                    source=self.name,
                    ingested_at=ingested_at,
                    source_record_id=f"{normalized}:{index}:{link}",
                    headline=title,
                    source_name=source_name,
                    url=link,
                    published_date=(
                        published_at.date()
                        if published_at is not None
                        else None
                    ),
                    published_at=published_at,
                    event_type="NEWS",
                    summary=description or None,
                    relevance=None,
                )
            )
        return tuple(output)


def _parse_pubdate(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _clean_html(value: str) -> str:
    text = html.unescape(_HTML_TAG.sub(" ", value))
    return " ".join(text.split())


__all__ = ["GoogleNewsRssAdapter"]
