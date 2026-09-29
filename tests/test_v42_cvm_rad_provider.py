from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs

import pytest

from b3_agent.providers.cvm_rad import (
    CvmRadAuthenticationError,
    CvmRadDisclosureProvider,
    CvmRadCredentialsMissing,
)


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


def test_cvm_rad_parses_ipe_link_and_preserves_metadata(monkeypatch):
    xml = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
<DownloadMultiplo DataSolicitada="29/09/2026 00:00" TipoDocumento="IPE">
  <Link url="https://example.test/doc.zip"
        Documento="IPE"
        ccvm="9512"
        DataRef="29/09/2026"
        Situacao="Liberado"
        Categoria="Fato Relevante"
        Tipo="Fato Relevante"
        Especie="Fato Relevante" />
</DownloadMultiplo>
"""
    seen = {}

    def fake_urlopen(request, timeout):
        seen["body"] = request.data.decode("ascii")
        seen["method"] = request.method
        return _Response(xml)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = CvmRadDisclosureProvider(
        username="user",
        password="secret",
        endpoint="https://cvm.test/rad",
    ).query_ipe(date(2026, 9, 29))

    assert len(result.disclosures) == 1
    item = result.disclosures[0]
    assert item.cvm_code == "9512"
    assert item.category == "Fato Relevante"
    assert item.source_status == "Liberado"
    assert item.reference_date == date(2026, 9, 29)
    assert item.document_url == "https://example.test/doc.zip"

    form = parse_qs(seen["body"])
    assert seen["method"] == "POST"
    assert form["txtDocumento"] == ["IPE"]
    assert form["txtAssuntoIPE"] == ["SIM"]
    assert form["txtData"] == ["29/09/2026"]
    assert form["txtHora"] == ["00:00"]


def test_cvm_rad_treats_22016_as_empty_not_failure(monkeypatch):
    xml = b"""<ERROS>
<NUMERO_DO_ERRO>22016</NUMERO_DO_ERRO>
<DESCRICAO_DO_ERRO>Nenhum documento encontrado</DESCRICAO_DO_ERRO>
</ERROS>"""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(xml),
    )

    result = CvmRadDisclosureProvider(
        username="user",
        password="secret",
        endpoint="https://cvm.test/rad",
    ).query_ipe(date(2026, 9, 29))

    assert result.disclosures == ()
    assert result.source_error_code == "22016"


def test_cvm_rad_bad_login_is_not_reported_as_empty(monkeypatch):
    xml = b"""<ERROS>
<NUMERO_DO_ERRO>1</NUMERO_DO_ERRO>
<DESCRICAO_DO_ERRO>Login incorreto</DESCRICAO_DO_ERRO>
</ERROS>"""
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(xml),
    )

    provider = CvmRadDisclosureProvider(
        username="bad",
        password="bad",
        endpoint="https://cvm.test/rad",
    )
    with pytest.raises(CvmRadAuthenticationError):
        provider.query_ipe(date(2026, 9, 29))


def test_cvm_rad_requires_runtime_credentials(monkeypatch):
    for name in ("CVM_DM_USER", "CVM_DM_PASS", "CVM_LOGIN", "CVM_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    provider = CvmRadDisclosureProvider()
    with pytest.raises(CvmRadCredentialsMissing):
        provider.query_ipe(date(2026, 9, 29))
