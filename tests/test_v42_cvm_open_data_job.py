from datetime import date, datetime, timezone
from types import SimpleNamespace

from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.jobs.cvm_open_data import CvmOpenDataBackfillJob
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIpeRecord,
    CvmOpenDataIssuerRecord,
    CvmOpenDataSecurityRecord,
)


NOW = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
DELIVERED = datetime(2026, 9, 29, 13, 0, tzinfo=timezone.utc)


class FakeOpenDataProvider:
    name = "cvm_open_data"

    def fetch_issuers(self):
        return SimpleNamespace(
            source_url="https://cvm.test/cad.csv",
            issuers=(
                CvmOpenDataIssuerRecord(
                    cvm_code="9512",
                    cnpj="33000167000101",
                    legal_name="PETROLEO BRASILEIRO S.A. PETROBRAS",
                    trading_name="PETROBRAS",
                    registration_status="ATIVO",
                    retrieved_at=NOW,
                    raw_row={},
                ),
            ),
        )

    def fetch_fca_securities(self, year):
        return SimpleNamespace(
            source_url=f"https://cvm.test/fca_{year}.zip",
            securities=(
                CvmOpenDataSecurityRecord(
                    cnpj="33000167000101",
                    company_name="PETROBRAS",
                    reference_date=date(2026, 1, 1),
                    ticker="PETR3",
                    security_type="Ações",
                    security_description="ON",
                    market="Bolsa",
                    exchange="B3",
                    trading_start=date(2000, 1, 1),
                    trading_end=None,
                    retrieved_at=NOW,
                    raw_row={},
                ),
                CvmOpenDataSecurityRecord(
                    cnpj="33000167000101",
                    company_name="PETROBRAS",
                    reference_date=date(2026, 1, 1),
                    ticker="PETR4",
                    security_type="Ações",
                    security_description="PN",
                    market="Bolsa",
                    exchange="B3",
                    trading_start=date(2000, 1, 1),
                    trading_end=None,
                    retrieved_at=NOW,
                    raw_row={},
                ),
            ),
        )

    def fetch_ipe_year(self, year, *, cvm_codes=(), cnpjs=(), categories=()):
        return SimpleNamespace(
            year=year,
            source_url=f"https://cvm.test/ipe_{year}.zip",
            retrieved_at=NOW,
            records=(
                CvmOpenDataIpeRecord(
                    provider_record_id="CVM_OPEN_DATA_IPE|123|1",
                    cnpj="33000167000101",
                    cvm_code="9512",
                    company_name="PETROBRAS",
                    reference_date=date(2026, 9, 29),
                    category="Fato Relevante",
                    disclosure_type="Fato Relevante",
                    species=None,
                    subject="Plano estratégico",
                    delivered_at=DELIVERED,
                    presentation_type=None,
                    protocol="123",
                    version="1",
                    document_url="https://www.rad.cvm.gov.br/doc/123",
                    retrieved_at=NOW,
                    raw_row={"categoria": "Fato Relevante"},
                ),
            ),
        )


def test_open_data_backfill_syncs_registry_and_persists_canonical_evidence(tmp_path):
    registry = IssuerRegistry(tmp_path / "issuer.sqlite3")
    job = CvmOpenDataBackfillJob(
        provider=FakeOpenDataProvider(),
        registry=registry,
        output_dir=tmp_path / "output",
    )

    result = job.run(
        year=2026,
        cvm_codes=("9512",),
        categories=("Fato Relevante",),
    )

    assert result["document_count"] == 1
    assert result["mapped_document_count"] == 1
    assert result["material_count"] == 1
    assert result["pit_status"] == "HISTORICAL_RECONSTRUCTION"
    assert result["registry_sync"]["security_count"] == 2

    item = result["disclosures"][0]
    assert item["ticker_refs"] == ["PETR3", "PETR4"]
    assert item["issuer_ref"] == "cvm:9512"
    assert item["materiality_reason"] == "OFFICIAL_FATO_RELEVANTE"
    assert item["evidence"]["metadata"]["authority_tier"] == 0
    assert item["evidence"]["metadata"]["discovery_channel"] == "CVM_OPEN_DATA"

    assert (tmp_path / "output" / "latest.json").is_file()
    assert len(list((tmp_path / "output" / "runs").glob("*.json"))) == 1
