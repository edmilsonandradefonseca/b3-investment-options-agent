from __future__ import annotations

import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from b3_agent import server
from b3_agent.intelligence.observability import (
    local_intelligence_manifests,
    local_intelligence_queues,
    local_intelligence_status,
    local_ticker_intelligence,
)
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.jobs.cvm_reconciliation import (
    CvmReconciliationJob,
    semantic_key_from_evidence,
    semantic_key_from_row,
)
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIssuerRecord,
    CvmOpenDataSecurityRecord,
)


NOW = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_observability_reads_cursor_queues_manifests_and_ticker(tmp_path):
    _write(
        tmp_path / "structured" / "cvm_rad_discovery_cursor.json",
        {
            "last_successful_requested_at": NOW.isoformat(),
            "last_successful_retrieval_at": NOW.isoformat(),
            "last_source_error": None,
            "overlap_minutes": 30,
        },
    )
    _write(
        tmp_path / "derived" / "continuous_intelligence" / "latest.json",
        {
            "status": "PASS",
            "completed_at": NOW.isoformat(),
            "metrics": {"documents": 3, "new_evidence": 2},
            "cursor": {"last_source_error": None},
        },
    )
    _write(
        tmp_path / "derived" / "local_relevance_screen" / "queue" / "r.json",
        {"request_id": "r", "ticker": "PETR4", "status": "PENDING"},
    )
    _write(
        tmp_path / "derived" / "local_evidence_analyst" / "queue" / "d.json",
        {"analysis_id": "d", "ticker": "PETR4", "status": "PENDING"},
    )
    _write(
        tmp_path / "derived" / "local_evidence_analyst" / "latest" / "PETR4.json",
        {"analysis_id": "d0", "ticker": "PETR4", "status": "READY"},
    )
    _write(
        tmp_path / "derived" / "local_relevance_screen" / "runs" / "r0.json",
        {
            "request_id": "r0",
            "ticker": "PETR4",
            "status": "READY",
            "created_at": NOW.isoformat(),
        },
    )

    status = local_intelligence_status(tmp_path)
    assert status["queues"]["relevance_pending"] == 1
    assert status["queues"]["dossier_pending"] == 1
    assert status["latest"]["discovery"]["documents"] == 3
    assert len(local_intelligence_queues(tmp_path)["relevance"]) == 1
    ticker = local_ticker_intelligence("PETR4", tmp_path)
    assert ticker["dossier"]["status"] == "READY"
    assert ticker["relevance"]["request_id"] == "r0"
    assert local_intelligence_manifests(tmp_path)["discovery"]["status"] == "PASS"


def test_server_local_observability_endpoints(monkeypatch):
    monkeypatch.setattr(
        server,
        "local_intelligence_status",
        lambda: {"status": "OK", "queues": {}},
    )
    monkeypatch.setattr(
        server,
        "local_intelligence_queues",
        lambda: {"relevance": [], "dossier": []},
    )
    monkeypatch.setattr(
        server,
        "local_intelligence_manifests",
        lambda: {"discovery": None},
    )
    monkeypatch.setattr(
        server,
        "local_ticker_intelligence",
        lambda ticker: {"ticker": ticker.upper(), "dossier": None, "relevance": None},
    )
    client = TestClient(server.app)
    assert client.get("/intelligence/local/status").status_code == 200
    assert client.get("/intelligence/local/queue").status_code == 200
    assert client.get("/intelligence/local/manifest").status_code == 200
    response = client.get("/intelligence/local/PETR4")
    assert response.status_code == 200
    assert response.json()["ticker"] == "PETR4"


class RegistryProvider:
    def fetch_issuers(self):
        return SimpleNamespace(
            source_url="x",
            issuers=(
                CvmOpenDataIssuerRecord(
                    cvm_code="9512",
                    cnpj="33000167000101",
                    legal_name="PETROBRAS",
                    trading_name="PETROBRAS",
                    registration_status="ATIVO",
                    retrieved_at=NOW,
                    raw_row={},
                ),
            ),
        )

    def fetch_fca_securities(self, year):
        return SimpleNamespace(
            source_url="x",
            securities=(
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


class FakeBackfill:
    def __init__(self, row):
        self.row = row

    def run(self, **kwargs):
        return {"disclosures": [self.row]}


def test_reconciliation_detects_and_persists_missing_historical_evidence(tmp_path):
    registry = IssuerRegistry(tmp_path / "issuer.sqlite3")
    registry.sync_from_cvm(provider=RegistryProvider(), year=2026, as_of=NOW.date())
    evidence = {
        "evidence_id": "CVM_OPEN_DATA_IPE:x",
        "title": "Fato Relevante",
        "content": "Category: Fato Relevante",
        "metadata": {
            "cvm_code": "9512",
            "reference_at": "2026-09-30T00:00:00-03:00",
            "pit_status": "HISTORICAL_RECONSTRUCTION",
            "extra": {
                "category": "Fato Relevante",
                "disclosure_type": "Fato Relevante",
                "species": None,
            },
        },
    }
    row = {
        "evidence_id": evidence["evidence_id"],
        "cvm_code": "9512",
        "reference_date": "2026-09-30",
        "delivered_at": "2026-09-30T12:00:00+00:00",
        "category": "Fato Relevante",
        "disclosure_type": "Fato Relevante",
        "species": None,
        "evidence": evidence,
    }
    assert semantic_key_from_row(row) == semantic_key_from_evidence(evidence)

    job = CvmReconciliationJob(
        registry=registry,
        backfill_job=FakeBackfill(row),
        continuous_root=tmp_path / "continuous",
        output_dir=tmp_path / "reconciliation",
    )
    result = job.run(
        year=2026,
        monitored_tickers=["PETR4"],
        as_of=date(2026, 9, 30),
    )
    assert result["status"] == "PASS"
    assert result["missing_from_live"] == 1
    assert result["reconciled_new"] == 1
    saved = list((tmp_path / "reconciliation" / "evidence").glob("*.json"))
    assert len(saved) == 1
    payload = json.loads(saved[0].read_text(encoding="utf-8"))
    assert payload["reconciliation_status"] == "HISTORICAL_RECONSTRUCTION"
