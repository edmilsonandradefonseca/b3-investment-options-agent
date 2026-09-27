from __future__ import annotations

from datetime import date
import json

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
    assert by_metric["profitMargins"].unit == "ratio"
    assert by_metric["ebitda"].quality_flags == ("availability_is_ingestion_time",)
    assert by_metric["ebitda"].report_date == date(2026, 9, 26)


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
