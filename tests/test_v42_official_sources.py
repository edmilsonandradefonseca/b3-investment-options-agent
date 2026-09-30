from datetime import date, datetime, timezone
from pathlib import Path
import resource
from types import SimpleNamespace

from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_sources import load_open_data_official_evidence
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIpeRecord,
    CvmOpenDataIssuerRecord,
    CvmOpenDataSecurityRecord,
)


NOW = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)


class FakeProvider:
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
        assert cvm_codes == ("9512",)
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
                    reference_date=date(2026, 9, 30),
                    category="Fato Relevante",
                    disclosure_type="Fato Relevante",
                    species=None,
                    subject="Evento material",
                    delivered_at=NOW,
                    presentation_type=None,
                    protocol="123",
                    version="1",
                    document_url="https://www.rad.cvm.gov.br/doc/123",
                    retrieved_at=NOW,
                    raw_row={"data_entrega": "2026-09-30"},
                ),
            ),
        )


def test_official_snapshot_loads_once_and_maps_evidence_to_each_security(tmp_path):
    snapshot = load_open_data_official_evidence(
        ["PETR4", "PETR3", "PETR4"],
        year=2026,
        provider=FakeProvider(),
        registry=IssuerRegistry(tmp_path / "issuer.sqlite3"),
    )

    assert snapshot.coverage["status"] == "SUCCESS"
    assert snapshot.coverage["requested_tickers"] == 2
    assert snapshot.coverage["resolved_tickers"] == 2
    assert snapshot.coverage["ipe_document_count"] == 1
    assert snapshot.coverage["ipe_material_count"] == 1
    assert snapshot.coverage["pit_status"] == "HISTORICAL_RECONSTRUCTION"

    assert len(snapshot.by_ticker["PETR3"]) == 1
    assert len(snapshot.by_ticker["PETR4"]) == 1
    evidence = snapshot.by_ticker["PETR4"][0]
    assert evidence.metadata.issuer_ref == "cvm:9512"
    assert evidence.metadata.materiality_reason == "OFFICIAL_FATO_RELEVANTE"


def test_official_snapshot_survives_low_nofile_with_many_ipe_records(tmp_path):
    class ManyRecordsProvider(FakeProvider):
        def fetch_ipe_year(self, year, *, cvm_codes=(), cnpjs=(), categories=()):
            assert cvm_codes == ("9512",)
            records = tuple(
                CvmOpenDataIpeRecord(
                    provider_record_id=f"CVM_OPEN_DATA_IPE|{index}|1",
                    cnpj="33000167000101",
                    cvm_code="9512",
                    company_name="PETROBRAS",
                    reference_date=date(2026, 9, 30),
                    category="Fato Relevante",
                    disclosure_type="Fato Relevante",
                    species=None,
                    subject=f"Evento material {index}",
                    delivered_at=NOW,
                    presentation_type=None,
                    protocol=str(index),
                    version="1",
                    document_url=f"https://www.rad.cvm.gov.br/doc/{index}",
                    retrieved_at=NOW,
                    raw_row={"data_entrega": "2026-09-30"},
                )
                for index in range(1000)
            )
            return SimpleNamespace(
                year=year,
                source_url=f"https://cvm.test/ipe_{year}.zip",
                retrieved_at=NOW,
                records=records,
            )

    fd_root = Path("/proc/self/fd")
    original_soft, original_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target_soft = min(original_soft, 128)
    if target_soft < 64:
        return

    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (target_soft, original_hard))
        before = len(list(fd_root.iterdir())) if fd_root.is_dir() else 0

        snapshot = load_open_data_official_evidence(
            ["PETR4", "PETR3"],
            year=2026,
            provider=ManyRecordsProvider(),
            registry=IssuerRegistry(tmp_path / "issuer-low-fd.sqlite3"),
        )

        assert snapshot.coverage["status"] == "SUCCESS"
        assert snapshot.coverage["ipe_document_count"] == 1000
        assert len(snapshot.by_ticker["PETR4"]) == 1000
        assert len(snapshot.by_ticker["PETR3"]) == 1000

        if fd_root.is_dir():
            after = len(list(fd_root.iterdir()))
            assert after <= before + 4
    finally:
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (original_soft, original_hard),
        )
