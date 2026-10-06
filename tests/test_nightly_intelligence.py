from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from b3_agent.intelligence.local_evidence_analysis import LocalEvidenceQueue
from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob
from b3_agent.knowledge.evidence import Evidence, EvidenceKind, EvidenceMetadata


class FakeNews:
    def __init__(self, *, material: bool):
        self.material = material

    def search(self, ticker, *, query=None, limit=8):
        now = datetime.now(timezone.utc)
        if self.material:
            headline = "Empresa anuncia resultado e dividendos"
            summary = "Lucro trimestral e dividendos foram anunciados."
            url = "https://example.com/news"
        else:
            headline = "PETR4 Cotação e indicadores"
            summary = "Página de consulta da ação."
            url = "https://statusinvest.com.br/acoes/petr4"
        return (SimpleNamespace(
            ticker=ticker,
            available_timestamp=now,
            observation_timestamp=now,
            published_date=now.date(),
            source_record_id="x",
            source="test",
            headline=headline,
            source_name="test",
            url=url,
            event_type="NEWS",
            summary=summary,
            relevance=None,
        ),)


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def ask(self, prompt):
        self.calls += 1
        return SimpleNamespace(
            model="deepseek-r1:8b",
            content="Summary: test",
            thinking="",
            total_duration_ns=1,
            eval_count=1,
            eval_duration_ns=1,
        )


def test_nightly_job_persists_manifest_for_material_event(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path, local_analysis_mode="inline")
    job.news = FakeNews(material=True)
    job.llm = FakeLLM()
    result = job.run(tickers=["PETR4"])
    assert result["ticker_count"] == 1
    assert result["completed"] == 1
    assert result["skipped"] == 0
    assert job.llm.calls == 1
    assert (tmp_path / "PETR4.json").is_file()
    assert (tmp_path / "latest.json").is_file()


def test_nightly_job_skips_static_non_material_page(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path, local_analysis_mode="inline")
    job.news = FakeNews(material=False)
    job.llm = FakeLLM()
    result = job.run(tickers=["PETR4"])
    assert result["completed"] == 0
    assert result["skipped"] == 1
    assert job.llm.calls == 0


def test_nightly_job_defers_after_deepseek_budget(tmp_path):
    job = NightlyIntelligenceJob(
        output_dir=tmp_path,
        max_deepseek_calls=1,
        local_analysis_mode="inline",
    )
    job.news = FakeNews(material=True)
    job.llm = FakeLLM()

    result = job.run(tickers=["PETR4", "VALE3"])

    assert result["completed"] == 1
    assert result["deferred"] == 1
    assert result["deepseek_calls"] == 1
    assert job.llm.calls == 1
    assert result["results"][1]["status"] == "deferred_deepseek_budget"


class FakeEmptyNews:
    last_diagnostics = SimpleNamespace(
        unresponsive_engines=(("bing news", "parsing error"),),
        fallback_used=True,
        fallback_strategy="general_unbounded",
        primary_raw_result_count=0,
        fallback_raw_result_count=0,
    )

    def search(self, ticker, *, query=None, limit=8):
        return ()


def test_nightly_job_distinguishes_insufficient_coverage_from_no_material(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path, local_analysis_mode="inline")
    job.news = FakeEmptyNews()
    job.llm = FakeLLM()

    result = job.run(tickers=["WEGE3"])

    assert result["completed"] == 0
    assert result["skipped"] == 0
    assert result["coverage_insufficient"] == 1
    assert job.llm.calls == 0

    item = result["results"][0]
    assert item["status"] == "coverage_insufficient"
    assert item["acquisition_status"] == "DEGRADED"
    assert item["evidence_conclusion"] == "COVERAGE_INSUFFICIENT"
    assert item["engine_errors"] == [
        {"engine": "bing news", "reason": "parsing error"}
    ]


def test_nightly_job_persists_coverage_metadata_for_no_material_result(tmp_path):
    job = NightlyIntelligenceJob(output_dir=tmp_path, local_analysis_mode="inline")
    job.news = FakeNews(material=False)
    job.llm = FakeLLM()

    result = job.run(tickers=["PETR4"])

    item = result["results"][0]
    assert item["status"] == "skipped_no_material_events"
    assert item["acquisition_status"] == "SUCCESS"
    assert item["evidence_conclusion"] == "NO_MATERIAL_FOUND"
    assert item["dated_result_count"] == 1
    assert item["dated_recent_count"] == 1


def test_official_material_evidence_triggers_deepseek_when_open_web_is_degraded(tmp_path):
    now = datetime.now(timezone.utc)
    official = Evidence(
        evidence_id="CVM_OPEN_DATA_IPE:abc",
        kind=EvidenceKind.DOCUMENT,
        title="Fato Relevante",
        content="Category: Fato Relevante\nSubject: evento oficial",
        source_url="https://www.rad.cvm.gov.br/doc/abc",
        metadata=EvidenceMetadata(
            document_id="123",
            source="CVM_OPEN_DATA_IPE",
            published_at=now,
            retrieved_at=now,
            ticker_refs=("PETR4",),
            issuer_ref="cvm:9512",
            cvm_code="9512",
            provider_record_id="CVM_OPEN_DATA_IPE|123|1",
            source_class="OFFICIAL_REGULATORY",
            authority_tier=0,
            discovery_channel="CVM_OPEN_DATA",
            transport_reliability="STRUCTURED_PUBLIC",
            first_seen_at=now,
            observed_at=now,
            acquisition_status="SUCCESS",
            pit_status="HISTORICAL_RECONSTRUCTION",
            materiality="MATERIAL",
            materiality_reason="OFFICIAL_FATO_RELEVANTE",
            materiality_policy_version="v4.2-official-1",
        ),
    )

    job = NightlyIntelligenceJob(output_dir=tmp_path, local_analysis_mode="inline")
    job.news = FakeEmptyNews()
    job.llm = FakeLLM()

    result = job.run(
        tickers=["PETR4"],
        official_evidence_by_ticker={"PETR4": (official,)},
    )

    item = result["results"][0]
    assert item["status"] == "completed"
    assert item["evidence_conclusion"] == "MATERIAL_FOUND"
    assert item["acquisition_status"] == "DEGRADED"
    assert item["official_evidence_count"] == 1
    assert item["official_material_count"] == 1
    assert item["material_evidence_count"] == 1
    assert job.llm.calls == 1
    assert item["source_refs"] == ["https://www.rad.cvm.gov.br/doc/abc"]
    assert item["evidence_events"][0]["materiality_reason"] == "OFFICIAL_FATO_RELEVANTE"


def test_v43_nightly_enqueues_material_analysis_without_calling_deepseek(tmp_path):
    queue = LocalEvidenceQueue(tmp_path / "local")
    job = NightlyIntelligenceJob(
        output_dir=tmp_path / "nightly",
        local_analysis_queue=queue,
    )
    job.news = FakeNews(material=True)
    job.llm = FakeLLM()

    result = job.run(tickers=["PETR4"])

    assert result["local_analysis_mode"] == "enqueue"
    assert result["queued_local_analysis"] == 1
    assert result["local_analysis_enqueues"] == 1
    assert result["deepseek_calls"] == 0
    assert job.llm.calls == 0
    assert result["results"][0]["status"] == "queued_local_analysis"
    assert result["results"][0]["local_analysis_queue_status"] == "ENQUEUED"
    assert len(queue.pending()) == 1


def test_v43_nightly_does_not_enqueue_no_material_or_coverage_gap(tmp_path):
    queue = LocalEvidenceQueue(tmp_path / "local")

    no_material = NightlyIntelligenceJob(
        output_dir=tmp_path / "no-material",
        local_analysis_mode="enqueue",
        local_analysis_queue=queue,
    )
    no_material.news = FakeNews(material=False)
    result_no_material = no_material.run(tickers=["PETR4"])

    assert result_no_material["skipped"] == 1
    assert result_no_material["queued_local_analysis"] == 0
    assert queue.pending() == []

    coverage = NightlyIntelligenceJob(
        output_dir=tmp_path / "coverage",
        local_analysis_mode="enqueue",
        local_analysis_queue=queue,
    )
    coverage.news = FakeEmptyNews()
    result_coverage = coverage.run(tickers=["WEGE3"])

    assert result_coverage["coverage_insufficient"] == 1
    assert result_coverage["queued_local_analysis"] == 0
    assert queue.pending() == []


def test_v43_nightly_enqueue_is_idempotent_for_same_material_bundle(tmp_path):
    queue = LocalEvidenceQueue(tmp_path / "local")
    job = NightlyIntelligenceJob(
        output_dir=tmp_path / "nightly",
        local_analysis_mode="enqueue",
        local_analysis_queue=queue,
    )
    job.news = FakeNews(material=True)

    first = job.run(tickers=["PETR4"])
    second = job.run(tickers=["PETR4"])

    assert first["results"][0]["local_analysis_queue_status"] == "ENQUEUED"
    assert second["results"][0]["local_analysis_queue_status"] == "ALREADY_QUEUED"
    assert len(queue.pending()) == 1


def test_nightly_runner_partitions_invalid_monitored_identities_without_raw_symbols():
    import importlib.util
    from pathlib import Path

    runner_path = Path(__file__).resolve().parents[1] / "scripts" / "run_nightly_intelligence.py"
    spec = importlib.util.spec_from_file_location("b3_nightly_runner", runner_path)
    runner = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(runner)

    valid, rejected_hashes = runner.partition_monitored_tickers(
        ["itub4", "ITUB4", "PETR4F", "bad identity", ""]
    )

    assert valid == ["ITUB4"]
    assert len(rejected_hashes) == 2
    assert all(len(value) == 12 for value in rejected_hashes)
    assert "PETR4F" not in rejected_hashes
    assert "BAD IDENTITY" not in rejected_hashes


def test_nightly_runner_rejects_only_invalid_identities():
    import importlib.util
    from pathlib import Path

    runner_path = Path(__file__).resolve().parents[1] / "scripts" / "run_nightly_intelligence.py"
    spec = importlib.util.spec_from_file_location("b3_nightly_runner", runner_path)
    runner = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(runner)

    valid, rejected_hashes = runner.partition_monitored_tickers(["PETR4F", "WEGE3X"])

    assert valid == []
    assert len(rejected_hashes) == 2
