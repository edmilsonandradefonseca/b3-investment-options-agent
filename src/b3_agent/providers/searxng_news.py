from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import re
import urllib.parse
import urllib.request
from urllib.parse import urlparse

from b3_agent.schemas.news import NewsEvidence


_RELATIVE_PT = re.compile(
    r"^h[áa]\\s+(?P<value>\\d+)\\s+(?P<unit>minuto|minutos|hora|horas|dia|dias)$",
    re.IGNORECASE,
)
_RELATIVE_EN = re.compile(
    r"^(?P<value>\\d+)\\s+(?P<unit>minute|minutes|hour|hours|day|days)\\s+ago$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SearxngSearchDiagnostics:
    query: str
    primary_category: str
    primary_raw_result_count: int
    fallback_raw_result_count: int
    normalized_result_count: int
    fallback_used: bool
    fallback_strategy: str | None
    unresponsive_engines: tuple[tuple[str, str], ...]


class SearxngNewsAdapter:
    """Acquire zero-cost web/news evidence through the shared local SearXNG service.

    V4.2 treats SearXNG as a discovery mechanism, not as an authority source.
    Freshness is enforced locally by B3 instead of relying exclusively on
    provider-specific time-range semantics.
    """

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
        self.last_diagnostics: SearxngSearchDiagnostics | None = None

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
        ingested_at = datetime.now(timezone.utc)

        primary = self._request(q=q, category="news")
        primary_results = _results(primary)
        all_unresponsive = list(_unresponsive_engines(primary))

        fallback_used = False
        fallback_strategy: str | None = None
        fallback_results: list[dict] = []
        primary_normalized = _normalize_results(
            primary_results[:limit],
            ticker=normalized,
            ingested_at=ingested_at,
            source=self.name,
        )
        primary_has_dated_evidence = any(
            record.published_at is not None for record in primary_normalized
        )

        # V4.2 fallback policy:
        # 1) NEWS without time_range to retain all news-capable engines.
        # 2) GENERAL + day when NEWS is empty or has no parseable dates.
        # 3) GENERAL without time_range only if the bounded fallback is also empty.
        if not primary_results or not primary_has_dated_evidence:
            fallback_used = True
            fallback_strategy = "general_day"
            fallback = self._request(q=q, category="general", time_range="day")
            fallback_results = _results(fallback)
            all_unresponsive.extend(_unresponsive_engines(fallback))

            if not fallback_results:
                fallback_strategy = "general_unbounded"
                fallback = self._request(q=q, category="general")
                fallback_results = _results(fallback)
                all_unresponsive.extend(_unresponsive_engines(fallback))

        merged = _deduplicate_results([*primary_results, *fallback_results])
        records = _normalize_results(
            merged[:limit],
            ticker=normalized,
            ingested_at=ingested_at,
            source=self.name,
        )

        self.last_diagnostics = SearxngSearchDiagnostics(
            query=q,
            primary_category="news",
            primary_raw_result_count=len(primary_results),
            fallback_raw_result_count=len(fallback_results),
            normalized_result_count=len(records),
            fallback_used=fallback_used,
            fallback_strategy=fallback_strategy,
            unresponsive_engines=tuple(dict.fromkeys(all_unresponsive)),
        )
        return records

    def _request(
        self,
        *,
        q: str,
        category: str,
        time_range: str | None = None,
    ) -> dict:
        params: dict[str, object] = {
            "q": q,
            "format": "json",
            "language": "pt-BR",
            "safesearch": 1,
            "categories": category,
        }
        if time_range:
            params["time_range"] = time_range

        encoded = urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}/search?{encoded}",
            headers={
                "User-Agent": "b3-investment-options-agent/0.1",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("SearXNG returned an invalid payload")
        return payload


def _results(payload: dict) -> list[dict]:
    results = payload.get("results", ())
    if not isinstance(results, list):
        raise ValueError("SearXNG returned an invalid results payload")
    return [item for item in results if isinstance(item, dict)]


def _unresponsive_engines(payload: dict) -> tuple[tuple[str, str], ...]:
    raw = payload.get("unresponsive_engines") or ()
    output: list[tuple[str, str]] = []
    if not isinstance(raw, list):
        return ()
    for item in raw:
        if isinstance(item, (list, tuple)) and item:
            name = str(item[0])
            reason = str(item[1]) if len(item) > 1 else "unknown"
            output.append((name, reason))
    return tuple(output)


def _deduplicate_results(results: list[dict]) -> list[dict]:
    output: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in results:
        title = " ".join(str(item.get("title") or "").lower().split())
        url = str(item.get("url") or "").strip()
        if not title or not url:
            continue
        key = (title, _canonical_url(url))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [
        (key, value)
        for key, value in query
        if not key.lower().startswith("utm_")
        and key.lower() not in {"gclid", "fbclid", "mc_cid", "mc_eid"}
    ]
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc.lower(), parsed.path, urllib.parse.urlencode(filtered), "")
    )


def _normalize_results(
    results: list[dict],
    *,
    ticker: str,
    ingested_at: datetime,
    source: str,
) -> tuple[NewsEvidence, ...]:
    output: list[NewsEvidence] = []
    for index, item in enumerate(results):
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title or not url:
            continue

        published_at = _published_at(
            item.get("publishedDate")
            or item.get("published_date")
            or item.get("pubdate"),
            relative_base=ingested_at,
        )
        published_date = published_at.date() if published_at is not None else None
        observation_timestamp = published_at or ingested_at

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
                instrument_id=ticker,
                ticker=ticker,
                observation_timestamp=observation_timestamp,
                available_timestamp=ingested_at,
                source=source,
                ingested_at=ingested_at,
                source_record_id=f"{ticker}:{index}:{_canonical_url(url)}",
                headline=title,
                source_name=source_name,
                url=url,
                published_date=published_date,
                published_at=published_at,
                event_type="NEWS",
                summary=str(item.get("content") or "").strip() or None,
                relevance=None,
            )
        )
    return tuple(output)


def _published_at(value: object, *, relative_base: datetime) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _aware_utc(value)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    try:
        return _aware_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        pass

    try:
        parsed_date = date.fromisoformat(text[:10])
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)
    except ValueError:
        pass

    lowered = text.lower().strip()
    if lowered in {"hoje", "today"}:
        return relative_base
    if lowered in {"ontem", "yesterday"}:
        return relative_base - timedelta(days=1)

    match = _RELATIVE_PT.match(lowered) or _RELATIVE_EN.match(lowered)
    if match:
        value_int = int(match.group("value"))
        unit = match.group("unit").lower()
        if unit.startswith("minuto") or unit.startswith("minute"):
            return relative_base - timedelta(minutes=value_int)
        if unit.startswith("hora") or unit.startswith("hour"):
            return relative_base - timedelta(hours=value_int)
        if unit.startswith("dia") or unit.startswith("day"):
            return relative_base - timedelta(days=value_int)

    return None


def _published_date(value: object) -> date | None:
    """Backward-compatible helper retained for existing callers/tests."""
    parsed = _published_at(value, relative_base=datetime.now(timezone.utc))
    return parsed.date() if parsed is not None else None


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
