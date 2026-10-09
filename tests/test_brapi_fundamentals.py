from __future__ import annotations

from datetime import date
import json
from urllib.error import HTTPError

from b3_agent.providers.brapi.fundamentals import BrapiFundamentalsAdapter


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_financial_data_maps_numeric_metrics(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "PETR4",
                "data": {
                    "symbol": "PETR4",
                    "ebitda": 1000,
                    "totalRevenue": 5000,
                    "profitMargins": 0.2,
                    "financialCurrency": "BRL",
                    "updatedAt": "2026-09-26T12:00:00.000Z",
                    "type": "financialData",
                },
            }
        ]
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    records = BrapiFundamentalsAdapter().get_financial_data("petr4")

    by_metric = {item.metric: item for item in records}
    assert by_metric["ebitda"].value == 1000.0
    assert by_metric["ebitda"].unit == "BRL"
    assert by_metric["profitMargins"].unit == "fraction"
    assert by_metric["ebitda"].quality_flags == ("availability_is_ingestion_time", "fiscal_period_not_verified")
    assert by_metric["ebitda"].report_date is None


def test_dividends_preserve_distinct_event_dates(monkeypatch):
    payload = {
        "results": [
            {
                "symbol": "PETR4",
                "data": {
                    "cashDividends": [
                        {
                            "assetIssued": "BRPETRACNPR6",
                            "paymentDate": "2026-10-20",
                            "rate": 0.75,
                            "relatedTo": "2T26",
                            "approvedOn": "2026-09-01",
                            "isinCode": "BRPETRACNPR6",
                            "label": "JCP",
                            "lastDatePrior": "2026-09-15",
                            "exDate": "2026-09-16",
                            "remarks": "",
                        }
                    ]
                },
            }
        ]
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    records = BrapiFundamentalsAdapter().get_dividends(
        "PETR4",
        start=date(2026, 1, 1),
        end=date(2026, 12, 31),
    )

    assert len(records) == 1
    item = records[0]
    assert item.payment_type == "JCP"
    assert item.announcement_date == date(2026, 9, 1)
    assert item.record_date == date(2026, 9, 15)
    assert item.ex_date == date(2026, 9, 16)
    assert item.payment_date == date(2026, 10, 20)
    assert item.gross_amount == 0.75
    assert item.reference_period == "2T26"


def test_brapi_token_is_sent_as_bearer(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "secret-token")
    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.headers.get("Authorization")
        return FakeResponse(
            {
                "results": [
                    {
                        "symbol": "PETR4",
                        "data": {
                            "ebitda": 1,
                            "updatedAt": "2026-09-26T12:00:00Z",
                        },
                    }
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    BrapiFundamentalsAdapter().get_financial_data("PETR4")

    assert captured["authorization"] == "Bearer secret-token"


def test_financial_data_403_falls_back_to_authenticated_quote_basics(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "secret-token")
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if "/api/v2/stocks/financial-data?" in request.full_url:
            raise HTTPError(
                request.full_url,
                403,
                "Forbidden",
                hdrs=None,
                fp=None,
            )
        assert request.headers.get("Authorization") == "Bearer secret-token"
        return FakeResponse(
            {
                "results": [
                    {
                        "symbol": "WEGE3",
                        "currency": "BRL",
                        "regularMarketTime": "2026-10-01T16:07:30.000Z",
                        "marketCap": 207534735768,
                        "priceEarnings": 31.25,
                        "earningsPerShare": 1.58,
                    }
                ],
                "requestedAt": "2026-10-01T16:07:31.000Z",
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    records = BrapiFundamentalsAdapter().get_financial_data("WEGE3")

    by_metric = {item.metric: item for item in records}
    assert set(by_metric) == {"marketCap", "priceEarnings", "earningsPerShare"}
    assert by_metric["marketCap"].unit == "BRL"
    assert by_metric["priceEarnings"].unit == "ratio"
    assert by_metric["earningsPerShare"].unit == "BRL/share"
    assert by_metric["earningsPerShare"].period_type == "CURRENT_SNAPSHOT"
    assert "brapi_quote_fallback" in by_metric["marketCap"].quality_flags
    assert calls[0].startswith(
        "https://brapi.dev/api/v2/stocks/financial-data?"
    )
    assert calls[1] == "https://brapi.dev/api/quote/WEGE3"


def test_dividend_403_uses_documented_quote_module_with_same_auth(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "test-token")
    calls=[]
    def get(request, timeout):
        calls.append(request)
        if len(calls)==1: raise HTTPError(request.full_url,403,"Forbidden",None,None)
        return FakeResponse({"results":[{"symbol":"BBDC4","dividendsData":{"cashDividends":[{"rate":.1,"approvedOn":"2026-09-01","lastDatePrior":"2026-10-01","paymentDate":"2026-10-15","label":"JCP"}]}}]})
    monkeypatch.setattr("urllib.request.urlopen",get)
    records=BrapiFundamentalsAdapter().get_dividends("BBDC4")
    assert records[0].gross_amount==.1
    assert calls[1].full_url.endswith("/BBDC4?dividends=true")
    assert calls[1].get_header("Authorization")=="Bearer test-token"


def test_dividend_fallback_rejects_sibling_ticker_and_missing_module(monkeypatch):
    import pytest
    for result in ({"symbol":"ITUB4","dividendsData":{}},{"symbol":"BBDC4"}):
        calls=[]
        def get(request,timeout):
            calls.append(request)
            if len(calls)==1: raise HTTPError(request.full_url,403,"Forbidden",None,None)
            return FakeResponse({"results":[result]})
        monkeypatch.setattr("urllib.request.urlopen",get)
        with pytest.raises(ValueError,match="exact ticker"):
            BrapiFundamentalsAdapter().get_dividends("BBDC4")


def test_provider_updated_at_is_not_fabricated_as_fiscal_report_date(monkeypatch):
    payload = {
        "results": [{
            "symbol": "ITUB4",
            "data": {
                "symbol": "ITUB4",
                "updatedAt": "2026-10-05T00:23:00.000Z",
                "financialCurrency": "BRL",
                "marketCap": 1000,
            },
        }]
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )

    records = BrapiFundamentalsAdapter().get_financial_data("ITUB4")

    assert records[0].report_date is None
    assert records[0].observation_timestamp.isoformat() == "2026-10-05T00:23:00+00:00"
    assert records[0].period_type == "CURRENT_SNAPSHOT"
