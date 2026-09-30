from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIssuerRecord,
    CvmOpenDataSecurityRecord,
)


NOW = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)


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
                    security_description="Ação Ordinária",
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
                    security_description="Ação Preferencial",
                    market="Bolsa",
                    exchange="B3",
                    trading_start=date(2000, 1, 1),
                    trading_end=None,
                    retrieved_at=NOW,
                    raw_row={},
                ),
            ),
        )


def test_issuer_registry_maps_one_issuer_to_multiple_tickers(tmp_path):
    registry = IssuerRegistry(tmp_path / "issuer_registry.sqlite3")

    summary = registry.sync_from_cvm(
        provider=FakeProvider(),
        year=2026,
        as_of=date(2026, 9, 30),
    )

    assert summary["issuer_count"] == 1
    assert summary["security_count"] == 2
    assert summary["active_security_count"] == 2
    assert summary["unmatched_security_count"] == 0

    assert registry.resolve_tickers(cvm_code="09512") == ("PETR3", "PETR4")
    assert registry.resolve_tickers(cnpj="33.000.167/0001-01") == ("PETR3", "PETR4")

    issuer = registry.resolve_issuer_by_ticker("petr4", as_of=date(2026, 9, 30))
    assert issuer is not None
    assert issuer.issuer_id == "cvm:9512"
    assert issuer.cnpj == "33000167000101"
    assert issuer.trading_name == "PETROBRAS"


def test_issuer_registry_excludes_ended_security_from_active_mapping(tmp_path):
    class HistoricalProvider(FakeProvider):
        def fetch_fca_securities(self, year):
            base = super().fetch_fca_securities(year)
            ended = CvmOpenDataSecurityRecord(
                cnpj="33000167000101",
                company_name="PETROBRAS",
                reference_date=date(2026, 1, 1),
                ticker="PETR9",
                security_type="Ações",
                security_description="Classe encerrada",
                market="Bolsa",
                exchange="B3",
                trading_start=date(2000, 1, 1),
                trading_end=date(2020, 12, 31),
                retrieved_at=NOW,
                raw_row={},
            )
            return SimpleNamespace(
                source_url=base.source_url,
                securities=base.securities + (ended,),
            )

    registry = IssuerRegistry(tmp_path / "issuer_registry.sqlite3")
    registry.sync_from_cvm(
        provider=HistoricalProvider(),
        year=2026,
        as_of=date(2026, 9, 30),
    )

    assert registry.resolve_tickers(cvm_code="9512") == ("PETR3", "PETR4")
    assert registry.resolve_tickers(
        cvm_code="9512",
        active_only=False,
    ) == ("PETR3", "PETR4", "PETR9")
