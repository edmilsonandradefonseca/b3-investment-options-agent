from __future__ import annotations

import json

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


def test_searxng_news_adapter_normalizes_results(monkeypatch):
    payload = {
        "results": [
            {
                "title": "PETR4 anuncia novo plano",
                "url": "https://example.com/petr4",
                "content": "Resumo da notícia",
                "publishedDate": "2026-09-27T10:30:00Z",
                "engine": "example",
            }
        ]
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(payload),
    )

    records = SearxngNewsAdapter(base_url="http://searxng").search("petr4")

    assert len(records) == 1
    assert records[0].ticker == "PETR4"
    assert records[0].headline == "PETR4 anuncia novo plano"
    assert records[0].published_date.isoformat() == "2026-09-27"
    assert records[0].source == "searxng"
    assert records[0].source_name == "example"
