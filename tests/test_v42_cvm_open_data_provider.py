from __future__ import annotations

from datetime import date
import io
from urllib.parse import urlsplit
import zipfile

from b3_agent.providers.cvm_open_data import CvmOpenDataProvider


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload


def _zip_csv(name: str, text: str, *, encoding: str = "latin-1") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, text.encode(encoding))
    return buffer.getvalue()


def test_cvm_open_data_ipe_preserves_reference_and_delivery_times(monkeypatch):
    csv_text = (
        "CNPJ_Companhia;Nome_Companhia;Data_Referencia;Codigo_CVM;"
        "Categoria;Tipo;Especie;Assunto;Data_Entrega;Tipo_Apresentacao;"
        "Protocolo_Entrega;Versao;Link_Download\n"
        "33.000.167/0001-01;PETROLEO BRASILEIRO S.A. PETROBRAS;"
        "2026-09-15;9512;Fato Relevante;Fato Relevante;;"
        "Novo plano estratégico;2026-09-16 08:30:00;Apresentação;"
        "123456;1;https://www.rad.cvm.gov.br/doc/123456\n"
    )
    payload = _zip_csv("ipe_cia_aberta_2026.csv", csv_text)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(payload),
    )

    result = CvmOpenDataProvider(
        ipe_url_template="https://cvm.test/ipe_{year}.zip"
    ).fetch_ipe_year(2026, categories=("Fato Relevante",))

    assert result.year == 2026
    assert len(result.records) == 1
    item = result.records[0]
    assert item.cnpj == "33000167000101"
    assert item.cvm_code == "9512"
    assert item.reference_date == date(2026, 9, 15)
    assert item.delivered_at is not None
    assert item.delivered_at.date() == date(2026, 9, 16)
    assert item.category == "Fato Relevante"
    assert item.protocol == "123456"
    assert item.provider_record_id == "CVM_OPEN_DATA_IPE|123456|1"
    assert item.document_url == "https://www.rad.cvm.gov.br/doc/123456"


def test_cvm_open_data_ipe_filters_by_cvm_code(monkeypatch):
    csv_text = (
        "CNPJ_Companhia;Data_Referencia;Codigo_CVM;Categoria;Tipo;"
        "Especie;Assunto;Data_Entrega;Tipo_Apresentacao;"
        "Protocolo_Entrega;Versao;Link_Download\n"
        "11111111000111;2026-09-01;1000;Comunicado ao Mercado;;;"
        "A;2026-09-01 10:00:00;;P1;1;https://example.test/1\n"
        "22222222000122;2026-09-02;2000;Fato Relevante;;;"
        "B;2026-09-02 10:00:00;;P2;1;https://example.test/2\n"
    )
    payload = _zip_csv("ipe_cia_aberta_2026.csv", csv_text)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(payload),
    )

    result = CvmOpenDataProvider(
        ipe_url_template="https://cvm.test/ipe_{year}.zip"
    ).fetch_ipe_year(2026, cvm_codes=("02000",))

    assert [record.protocol for record in result.records] == ["P2"]


def test_cvm_open_data_parses_cad_and_fca_security_mapping(monkeypatch):
    cad = (
        "CNPJ_CIA;DENOM_SOCIAL;DENOM_COMERC;CD_CVM;SIT\n"
        "33.000.167/0001-01;PETROLEO BRASILEIRO S.A. PETROBRAS;"
        "PETROBRAS;9512;ATIVO\n"
    ).encode("latin-1")
    fca_text = (
        "CNPJ_Companhia;Data_Referencia;Nome_Companhia;"
        "Tipo_Valor_Mobiliario;Valor_Mobiliario;Mercado;"
        "Sigla_Entidade_Administradora;Codigo_Negociacao;"
        "Data_Inicio_Negociacao;Data_Fim_Negociacao\n"
        "33.000.167/0001-01;2026-01-01;PETROBRAS;Ações;"
        "Ação Ordinária;Bolsa;B3;PETR3;2000-01-01;\n"
        "33.000.167/0001-01;2026-01-01;PETROBRAS;Ações;"
        "Ação Preferencial;Bolsa;B3;PETR4;2000-01-01;\n"
    )
    fca = _zip_csv(
        "fca_cia_aberta_valor_mobiliario_2026.csv",
        fca_text,
    )

    def fake_urlopen(request, timeout):
        path = urlsplit(request.full_url).path
        if path.endswith("cad_cia_aberta.csv"):
            return _Response(cad)
        return _Response(fca)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    provider = CvmOpenDataProvider(
        cad_url="https://cvm.test/cad_cia_aberta.csv",
        fca_url_template="https://cvm.test/fca_{year}.zip",
    )
    issuer_result = provider.fetch_issuers()
    security_result = provider.fetch_fca_securities(2026)

    assert len(issuer_result.issuers) == 1
    issuer = issuer_result.issuers[0]
    assert issuer.cvm_code == "9512"
    assert issuer.cnpj == "33000167000101"
    assert issuer.trading_name == "PETROBRAS"

    assert [item.ticker for item in security_result.securities] == ["PETR3", "PETR4"]
    assert all(item.is_active(as_of=date(2026, 9, 30)) for item in security_result.securities)
