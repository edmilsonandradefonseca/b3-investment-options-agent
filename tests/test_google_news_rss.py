from __future__ import annotations

from datetime import timezone
import urllib.parse

from b3_agent.providers.google_news_rss import GoogleNewsRssAdapter


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Ibovespa sobe com bancos e commodities</title>
      <link>https://news.google.com/rss/articles/example</link>
      <pubDate>Thu, 01 Oct 2026 14:30:00 GMT</pubDate>
      <description><![CDATA[<b>Mercado</b> acompanha juros e dolar.]]></description>
      <source url="https://example.com">Example News</source>
    </item>
  </channel>
</rss>
"""


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return RSS


def test_google_news_rss_normalizes_brazil_market_feed(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr(
        "b3_agent.providers.google_news_rss.urllib.request.urlopen",
        fake_urlopen,
    )
    adapter = GoogleNewsRssAdapter(timeout=7)
    records = adapter.search(
        "IBOV",
        query="Ibovespa mercado Brasil when:1d",
        limit=5,
    )

    assert len(records) == 1
    record = records[0]
    assert record.ticker == "IBOV"
    assert record.source == "google_news_rss"
    assert record.source_name == "Example News"
    assert record.headline == "Ibovespa sobe com bancos e commodities"
    assert record.summary == "Mercado acompanha juros e dolar."
    assert record.published_at is not None
    assert record.published_at.tzinfo == timezone.utc
    assert record.published_date.isoformat() == "2026-10-01"

    query = urllib.parse.parse_qs(
        urllib.parse.urlsplit(seen["url"]).query
    )
    assert query["hl"] == ["pt-BR"]
    assert query["gl"] == ["BR"]
    assert query["ceid"] == ["BR:pt-419"]
    assert "when:1d" in query["q"][0]
    assert seen["timeout"] == 7


def test_google_news_rss_rejects_invalid_xml(monkeypatch):
    class BadResponse(Response):
        def read(self):
            return b"<rss>"

    monkeypatch.setattr(
        "b3_agent.providers.google_news_rss.urllib.request.urlopen",
        lambda request, timeout: BadResponse(),
    )
    try:
        GoogleNewsRssAdapter().search("IBOV")
    except ValueError as exc:
        assert "invalid XML" in str(exc)
    else:
        raise AssertionError("invalid RSS must fail explicitly")
