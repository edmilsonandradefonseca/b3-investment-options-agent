from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

from b3_agent.providers.searxng_news import SearxngNewsAdapter


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_searxng_news_adapter_normalizes_results_without_primary_time_range(monkeypatch):
    payload = {
        "results": [
            {
                "title": "PETR4 anuncia novo plano",
                "url": "https://example.com/petr4?utm_source=test",
                "content": "Resumo da notícia",
                "publishedDate": "2026-09-27T10:30:00Z",
                "engine": "example",
            }
        ]
    }
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        return _Response(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    adapter = SearxngNewsAdapter(base_url="http://searxng")
    records = adapter.search("petr4")

    assert len(records) == 1
    assert records[0].ticker == "PETR4"
    assert records[0].headline == "PETR4 anuncia novo plano"
    assert records[0].published_date.isoformat() == "2026-09-27"
    assert records[0].published_at.isoformat() == "2026-09-27T10:30:00+00:00"
    assert records[0].source == "searxng"
    assert records[0].source_name == "example"
    query = parse_qs(urlsplit(seen[0]).query)
    assert query["categories"] == ["news"]
    assert "time_range" not in query
    assert adapter.last_diagnostics is not None
    assert adapter.last_diagnostics.fallback_used is False


def test_searxng_falls_back_to_general_and_parses_relative_portuguese_date(monkeypatch):
    responses = iter([
        {
            "results": [],
            "unresponsive_engines": [["bing news", "parsing error"]],
        },
        {
            "results": [
                {
                    "title": "WEG anuncia investimento relevante",
                    "url": "https://example.com/wege3",
                    "content": "Investimento e capex anunciados.",
                    "publishedDate": "há 8 horas",
                    "engine": "brave",
                }
            ],
            "unresponsive_engines": [],
        },
    ])
    seen = []

    def fake_urlopen(request, timeout):
        seen.append(request.full_url)
        return _Response(next(responses))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    adapter = SearxngNewsAdapter(base_url="http://searxng")
    records = adapter.search("WEGE3")

    assert len(records) == 1
    assert records[0].published_at is not None
    assert records[0].published_date is not None
    assert len(seen) == 2
    fallback_query = parse_qs(urlsplit(seen[1]).query)
    assert fallback_query["categories"] == ["general"]
    assert fallback_query["time_range"] == ["day"]

    diagnostics = adapter.last_diagnostics
    assert diagnostics is not None
    assert diagnostics.fallback_used is True
    assert diagnostics.fallback_strategy == "general_day"
    assert diagnostics.primary_raw_result_count == 0
    assert diagnostics.fallback_raw_result_count == 1
    assert ("bing news", "parsing error") in diagnostics.unresponsive_engines


def test_searxng_falls_back_when_news_results_have_no_parseable_dates(monkeypatch):
    responses = iter([
        {
            "results": [
                {
                    "title": "WEGE3 overview",
                    "url": "https://example.com/static",
                    "publishedDate": None,
                    "engine": "example",
                }
            ]
        },
        {
            "results": [
                {
                    "title": "WEGE3 resultado recente",
                    "url": "https://example.com/recent",
                    "publishedDate": "2026-09-29T12:00:00Z",
                    "engine": "brave",
                }
            ]
        },
    ])

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(next(responses)),
    )

    adapter = SearxngNewsAdapter(base_url="http://searxng")
    records = adapter.search("WEGE3")

    assert len(records) == 2
    assert any(record.published_at is not None for record in records)
    assert adapter.last_diagnostics is not None
    assert adapter.last_diagnostics.fallback_used is True
