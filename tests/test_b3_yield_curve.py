from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

import pyettj.ettj as pyettj_ettj
from b3_agent.providers.b3_yield_curve import (
    B3YieldCurveAdapter,
    YieldCurveProviderError,
)


class FakeResponse:
    content = b"verified-download"

    def __init__(self):
        self.raised = False

    def raise_for_status(self):
        self.raised = True


def test_curve_adapter_keeps_tls_verification_and_normalizes_pyettj_rows(monkeypatch):
    calls = {}

    monkeypatch.setattr(pyettj_ettj, "_montar_url", lambda value: "https://b3.test/taxaswap")
    monkeypatch.setattr(pyettj_ettj, "_extrair_txt", lambda raw, label: "parsed")
    monkeypatch.setattr(
        pyettj_ettj,
        "_parsear_txt",
        lambda text, curves, ref: pd.DataFrame(
            [
                {
                    "refdate": pd.Timestamp(ref),
                    "curva": "PRE",
                    "descricao": "DIxPRE",
                    "dias_corridos": 252,
                    "dias_uteis": 174,
                    "taxa": 0.1465,
                    "vertice": "F",
                }
            ]
        ),
    )
    monkeypatch.setattr(pyettj_ettj, "_validar_output", lambda frame, curves, label: None)

    def http_get(url, **kwargs):
        calls.update(url=url, **kwargs)
        return FakeResponse()

    rows = B3YieldCurveAdapter(http_get=http_get).get_latest(
        "PRE", as_of=date(2026, 9, 24)
    )

    assert calls["verify"] is True
    assert calls["url"] == "https://b3.test/taxaswap"
    assert rows[0].curve_code == "PRE"
    assert rows[0].curve_description == "DIxPRE"
    assert rows[0].days_calendar == 252
    assert rows[0].rate_decimal == pytest.approx(0.1465)


def test_curve_adapter_rejects_unknown_curve_before_network_call():
    adapter = B3YieldCurveAdapter(http_get=lambda *args, **kwargs: pytest.fail("network called"))
    with pytest.raises(ValueError, match="unsupported yield curve"):
        adapter.get_latest("IPCA")


def test_empty_b3_archive_falls_back_to_previous_published_day(monkeypatch):
    import io
    import zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w'):
        pass
    dates = []
    monkeypatch.setattr(pyettj_ettj, '_montar_url', lambda ref: dates.append(ref) or str(ref))
    monkeypatch.setattr(pyettj_ettj, '_extrair_txt', lambda raw, label: 'parsed')
    monkeypatch.setattr(pyettj_ettj, '_parsear_txt', lambda text, curves, ref: pd.DataFrame([
        dict(curva='PRE', descricao='DIxPRE', dias_corridos=30, dias_uteis=21, taxa=.14, vertice='F')
    ]))
    monkeypatch.setattr(pyettj_ettj, '_validar_output', lambda *args: None)
    def get(url, **kwargs):
        response = FakeResponse()
        response.content = buffer.getvalue() if len(dates) == 1 else b'published'
        return response
    rows = B3YieldCurveAdapter(http_get=get).get_latest('PRE', as_of=date(2026, 10, 9))
    assert dates == [date(2026, 10, 9), date(2026, 10, 8)]
    assert rows[0].observation_timestamp.date() == date(2026, 10, 8)


def test_malformed_archive_does_not_silently_fall_back(monkeypatch):
    def fail(*args):
        raise RuntimeError('corrupted archive')
    monkeypatch.setattr(pyettj_ettj, '_extrair_txt', fail)
    with pytest.raises(YieldCurveProviderError) as error:
        B3YieldCurveAdapter(http_get=lambda *args, **kwargs: FakeResponse()).get_latest('PRE')
    assert error.value.code == 'PROVIDER_ERROR'
