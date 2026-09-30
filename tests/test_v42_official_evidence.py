from datetime import date, datetime, timezone
from types import SimpleNamespace

from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_evidence import (
    OfficialEvidenceBuilder,
    evidence_to_dict,
)
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIpeRecord,
    CvmOpenDataIssuerRecord,
    CvmOpenDataSecurityRecord,
)
from b3_agent.providers.cvm_rad import CvmRadDisclosure


NOW = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)
DELIVERED = datetime(2026, 9, 29, 13, 30, tzinfo=timezone.utc)


class RegistryProvider:
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


def _registry(tmp_path):
    registry = IssuerRegistry(tmp_path / "issuer.sqlite3")
    registry.sync_from_cvm(
        provider=RegistryProvider(),
        year=2026,
        as_of=date(2026, 9, 30),
    )
    return registry


def test_open_data_ipe_becomes_canonical_historical_evidence(tmp_path):
    builder = OfficialEvidenceBuilder(registry=_registry(tmp_path))
    record = CvmOpenDataIpeRecord(
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
        presentation_type="Apresentação",
        protocol="123",
        version="1",
        document_url="https://www.rad.cvm.gov.br/doc/123",
        retrieved_at=NOW,
        raw_row={"categoria": "Fato Relevante", "data_entrega": "2026-09-29"},
    )

    evidence = builder.from_open_data_ipe(record)

    assert evidence.kind.value == "document"
    assert evidence.metadata.issuer_ref == "cvm:9512"
    assert evidence.metadata.ticker_refs == ("PETR3", "PETR4")
    assert evidence.metadata.materiality == "MATERIAL"
    assert evidence.metadata.materiality_reason == "OFFICIAL_FATO_RELEVANTE"
    assert evidence.metadata.pit_status == "HISTORICAL_RECONSTRUCTION"
    assert evidence.metadata.reference_at is not None
    assert evidence.metadata.reference_at.date() == date(2026, 9, 29)
    assert evidence.metadata.published_at == DELIVERED
    assert evidence.metadata.first_seen_at == NOW
    assert evidence.metadata.discovery_channel == "CVM_OPEN_DATA"
    assert evidence.metadata.extra["published_at_precision"] == "DATE"
    assert evidence.metadata.extra["published_at_semantics"] == "CVM_DATA_ENTREGA"

    payload = evidence_to_dict(evidence)
    assert payload["metadata"]["ticker_refs"] == ["PETR3", "PETR4"]
    assert payload["metadata"]["pit_status"] == "HISTORICAL_RECONSTRUCTION"


def test_rad_becomes_live_observed_evidence_without_inventing_publish_time(tmp_path):
    builder = OfficialEvidenceBuilder(registry=_registry(tmp_path))
    record = CvmRadDisclosure(
        provider_record_id="CVM_RAD|2026-09-30|9512|IPE|30/09/2026|https://x|0",
        document_url="https://www.rad.cvm.gov.br/doc/live",
        document_type="IPE",
        cvm_code="9512",
        reference_date=date(2026, 9, 30),
        source_status="Liberado",
        category="Comunicado ao Mercado",
        disclosure_type="Comunicado ao Mercado",
        species=None,
        retrieved_at=NOW,
        raw_attributes={"Categoria": "Comunicado ao Mercado"},
    )

    evidence = builder.from_rad(record)

    assert evidence.metadata.issuer_ref == "cvm:9512"
    assert evidence.metadata.ticker_refs == ("PETR3", "PETR4")
    assert evidence.metadata.materiality == "CANDIDATE"
    assert evidence.metadata.pit_status == "OBSERVED_LIVE"
    assert evidence.metadata.published_at is None
    assert evidence.metadata.first_seen_at == NOW
    assert evidence.metadata.observed_at == NOW
    assert evidence.metadata.discovery_channel == "CVM_RAD"
