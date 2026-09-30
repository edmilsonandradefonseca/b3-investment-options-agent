from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from b3_agent.intelligence.continuous_triage import (
    ContinuousTriageAction,
    triage_official_evidence,
)
from b3_agent.intelligence.discovery_cursor import DiscoveryCursorStore
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.intelligence.official_evidence import OfficialEvidenceBuilder
from b3_agent.intelligence.relevance_screen import (
    LocalRelevanceAnalyst,
    LocalRelevanceQueue,
    RelevanceStatus,
    promote_to_dossier,
)
from b3_agent.jobs.continuous_intelligence import ContinuousIntelligenceJob
from b3_agent.providers.cvm_open_data import (
    CvmOpenDataIssuerRecord,
    CvmOpenDataSecurityRecord,
)
from b3_agent.providers.cvm_rad import CvmRadDisclosure


NOW = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)


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
        as_of=NOW.date(),
    )
    return registry


def _disclosure(*, material=True, suffix="1"):
    category = "Fato Relevante" if material else "Comunicado ao Mercado"
    return CvmRadDisclosure(
        provider_record_id=f"CVM_RAD|{suffix}",
        document_url=f"https://cvm.test/{suffix}.zip",
        document_type="IPE",
        cvm_code="9512",
        reference_date=NOW.date(),
        source_status="Liberado",
        category=category,
        disclosure_type=category,
        species=None,
        retrieved_at=NOW,
        raw_attributes={"Categoria": category},
    )


class FakeRadProvider:
    name = "cvm_rad"

    def __init__(self, disclosures):
        self.disclosures = tuple(disclosures)
        self.calls = []

    def query_ipe(self, requested_date, *, requested_time="00:00"):
        self.calls.append((requested_date, requested_time))
        return SimpleNamespace(
            requested_date=requested_date,
            requested_time=requested_time,
            source_error_code=None,
            disclosures=self.disclosures,
        )


class FailingProvider:
    name = "cvm_rad"

    def query_ipe(self, requested_date, *, requested_time="00:00"):
        raise RuntimeError("source down")


class FakeRelevanceClient:
    model = "deepseek-r1:8b"
    num_predict = 64

    def __init__(self, relevance="RELEVANT", refs=None, eval_count=20):
        self.relevance = relevance
        self.refs = refs or ["https://cvm.test/2.zip"]
        self.eval_count = eval_count

    def ask(self, prompt):
        import json
        return SimpleNamespace(
            model=self.model,
            content=json.dumps(
                {
                    "relevance": self.relevance,
                    "themes": ["governance"],
                    "reason": "candidate may affect monitored issuer",
                    "senior_review_candidate": False,
                    "evidence_refs": self.refs,
                }
            ),
            thinking="",
            eval_count=self.eval_count,
            total_duration_ns=10,
        )


def test_cursor_overlap_restart_and_error_does_not_advance(tmp_path):
    store = DiscoveryCursorStore(
        tmp_path / "cursor.json",
        overlap_minutes=30,
        initial_lookback_hours=24,
    )
    start, end = store.query_window(now=NOW)
    assert end == NOW
    assert start == NOW - timedelta(hours=24)

    committed = store.commit_success(
        requested_through=NOW,
        retrieval_at=NOW,
        provider_ids=["A"],
        processed_evidence_keys=["E1"],
    )
    restart = DiscoveryCursorStore(
        tmp_path / "cursor.json",
        overlap_minutes=30,
        initial_lookback_hours=24,
    )
    next_start, _ = restart.query_window(now=NOW + timedelta(hours=1))
    assert next_start == NOW - timedelta(minutes=30)

    failed = restart.record_error("boom", previous=committed)
    assert failed.last_successful_requested_at == NOW.isoformat()
    assert restart.load().last_source_error == "boom"


def test_deterministic_triage_material_candidate_and_non_material(tmp_path):
    builder = OfficialEvidenceBuilder(registry=_registry(tmp_path))
    material = builder.from_rad(_disclosure(material=True, suffix="1"))
    candidate = builder.from_rad(_disclosure(material=False, suffix="2"))
    other = CvmRadDisclosure(
        provider_record_id="CVM_RAD|3",
        document_url="https://cvm.test/3.zip",
        document_type="IPE",
        cvm_code="9512",
        reference_date=NOW.date(),
        source_status="Liberado",
        category="Acordo de Acionistas",
        disclosure_type="Acordo de Acionistas",
        species=None,
        retrieved_at=NOW,
        raw_attributes={},
    )
    non_material = builder.from_rad(other)

    assert triage_official_evidence(
        material, monitored_tickers=["PETR4"], as_of=NOW
    ).action == ContinuousTriageAction.DOSSIER
    assert triage_official_evidence(
        candidate, monitored_tickers=["PETR4"], as_of=NOW
    ).action == ContinuousTriageAction.RELEVANCE_SCREEN
    assert triage_official_evidence(
        non_material, monitored_tickers=["PETR4"], as_of=NOW
    ).action == ContinuousTriageAction.SKIP
    assert triage_official_evidence(
        material, monitored_tickers=["VALE3"], as_of=NOW
    ).reason == "OUTSIDE_MONITORED_UNIVERSE"


def test_continuous_job_persists_dedupes_and_routes_without_inline_llm(tmp_path):
    registry = _registry(tmp_path)
    provider = FakeRadProvider(
        [
            _disclosure(material=True, suffix="1"),
            _disclosure(material=False, suffix="2"),
        ]
    )
    cursor = DiscoveryCursorStore(
        tmp_path / "cursor.json",
        overlap_minutes=30,
        initial_lookback_hours=1,
    )
    dossier = LocalEvidenceQueue(tmp_path / "dossier")
    relevance = LocalRelevanceQueue(tmp_path / "relevance")
    job = ContinuousIntelligenceJob(
        provider=provider,
        registry=registry,
        cursor_store=cursor,
        dossier_queue=dossier,
        relevance_queue=relevance,
        root=tmp_path / "continuous",
    )

    first = job.run(now=NOW, monitored_tickers=["PETR4"])
    assert first["status"] == "PASS"
    assert first["deepseek_called_inline"] is False
    assert first["metrics"]["new_evidence"] == 2
    assert first["metrics"]["dossier_enqueued"] == 1
    assert first["metrics"]["relevance_enqueued"] == 1
    assert len(dossier.pending()) == 1
    assert len(relevance.pending()) == 1

    second = job.run(
        now=NOW + timedelta(minutes=15),
        monitored_tickers=["PETR4"],
    )
    assert second["metrics"]["new_evidence"] == 0
    assert second["metrics"]["duplicates"] == 2
    assert second["metrics"]["dossier_enqueued"] == 0
    assert second["metrics"]["relevance_enqueued"] == 0
    assert len(dossier.pending()) == 1
    assert len(relevance.pending()) == 1


def test_cursor_does_not_advance_when_source_fails(tmp_path):
    registry = _registry(tmp_path)
    cursor = DiscoveryCursorStore(
        tmp_path / "cursor.json",
        overlap_minutes=30,
        initial_lookback_hours=1,
    )
    job = ContinuousIntelligenceJob(
        provider=FailingProvider(),
        registry=registry,
        cursor_store=cursor,
        dossier_queue=LocalEvidenceQueue(tmp_path / "dossier"),
        relevance_queue=LocalRelevanceQueue(tmp_path / "relevance"),
        root=tmp_path / "continuous",
    )
    with pytest.raises(RuntimeError, match="source down"):
        job.run(now=NOW, monitored_tickers=["PETR4"])
    state = cursor.load()
    assert state.last_successful_requested_at is None
    assert "source down" in (state.last_source_error or "")


def test_relevance_screen_promotes_relevant_candidate_only(tmp_path):
    queue = LocalRelevanceQueue(tmp_path / "relevance")
    dossier = LocalEvidenceQueue(tmp_path / "dossier")
    event = {
        "evidence_type": "official_disclosure",
        "evidence_id": "E2",
        "source_ref": "https://cvm.test/2.zip",
        "headline": "Comunicado ao Mercado",
        "summary": "Candidate event",
        "materiality": "CANDIDATE",
        "pit_status": "OBSERVED_LIVE",
    }
    request, status = queue.enqueue("PETR4", [event])
    assert status == "ENQUEUED"
    result = LocalRelevanceAnalyst(FakeRelevanceClient()).analyze(request)
    assert result.status == RelevanceStatus.READY
    assert promote_to_dossier(request, result, dossier) == "ENQUEUED"
    assert len(dossier.pending()) == 1

    queue2 = LocalRelevanceQueue(tmp_path / "relevance2")
    dossier2 = LocalEvidenceQueue(tmp_path / "dossier2")
    request2, _ = queue2.enqueue("PETR4", [event])
    result2 = LocalRelevanceAnalyst(
        FakeRelevanceClient(relevance="NOT_RELEVANT")
    ).analyze(request2)
    assert promote_to_dossier(request2, result2, dossier2) == "NOT_PROMOTED"
    assert len(dossier2.pending()) == 0
