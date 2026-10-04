from __future__ import annotations

import json
from dataclasses import replace

import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from b3_agent.intelligence.local_evidence_analysis import (
    LocalAnalysisStatus,
    LocalEvidenceAnalyst,
    LocalEvidenceContextSelector,
    LocalEvidenceDossier,
    LocalEvidenceQueue,
    LOCAL_ANALYSIS_SCHEMA,
    build_request,
    evidence_fingerprint,
)
from b3_agent.intelligence.senior_context import SeniorEvidenceContextBuilder
from b3_agent.jobs.local_evidence_analyst import LocalEvidenceAnalystJob
from b3_agent.llm.ollama_client import OllamaClient


@pytest.mark.parametrize("empty_refs", [False, True])
def test_generation_schema_restricts_refs_without_mutating_shared_client(monkeypatch, empty_refs):
    request = build_request("PETR4", _events())
    if empty_refs:
        request = replace(request, source_refs=())
    client = OllamaClient(model="deepseek-r1:8b", num_ctx=4096,
                          num_predict=2048, think=False,
                          format_schema=LOCAL_ANALYSIS_SCHEMA)
    observed = []

    def ask(runtime_client, prompt):
        observed.append(runtime_client)
        result = FakeClient().ask(prompt)
        payload = json.loads(result.content)
        payload["evidence_refs"] = list(request.source_refs)
        result.content = json.dumps(payload)
        return result

    monkeypatch.setattr(OllamaClient, "ask", ask)
    assert LocalEvidenceAnalyst(client).analyze(request).status == LocalAnalysisStatus.READY
    generated = observed[0]
    assert generated is not client
    refs = generated.format_schema["properties"]["evidence_refs"]
    if empty_refs:
        assert refs["maxItems"] == 0
        assert "enum" not in refs["items"]
    else:
        assert refs["items"]["enum"] == list(request.source_refs)
    assert "enum" not in LOCAL_ANALYSIS_SCHEMA["properties"]["evidence_refs"]["items"]
    for field in ("base_url", "model", "timeout", "num_ctx", "num_predict", "keep_alive", "think"):
        assert getattr(generated, field) == getattr(client, field)


@pytest.mark.parametrize("field,value", [("risks", [123]), ("evidence_refs", [123]), ("extra", "unexpected")])
def test_post_generation_validation_rejects_malformed_structured_fields(field, value):
    class MalformedClient(FakeClient):
        def ask(self, prompt):
            result = super().ask(prompt)
            payload = json.loads(result.content)
            payload[field] = value
            result.content = json.dumps(payload)
            return result

    dossier = LocalEvidenceAnalyst(MalformedClient()).analyze(build_request("PETR4", _events()))
    assert dossier.status == LocalAnalysisStatus.DEGRADED
    assert "INVALID_SCHEMA" in dossier.quality_flags


def _events():
    return [
        {
            "evidence_type": "official_disclosure",
            "evidence_id": "E1",
            "source_ref": "https://cvm.test/e1",
            "published_at": "2026-09-30T10:00:00+00:00",
            "headline": "Fato Relevante",
            "summary": "Evento oficial",
            "materiality": "MATERIAL",
            "materiality_reason": "OFFICIAL_FATO_RELEVANTE",
            "pit_status": "OBSERVED_LIVE",
        },
        {
            "evidence_type": "open_web_event",
            "source_ref": "https://news.test/e2",
            "published_at": "2026-09-30T10:01:00+00:00",
            "headline": "Cobertura",
            "summary": "Cobertura do mesmo evento",
        },
    ]


class FakeClient:
    model = "deepseek-r1:8b"
    num_predict = 256

    def __init__(self, *, eval_count=80, refs=None, invalid_json=False):
        self.eval_count = eval_count
        self.refs = refs or ["https://cvm.test/e1"]
        self.invalid_json = invalid_json
        self.calls = 0

    def ask(self, prompt):
        self.calls += 1
        content = (
            "not-json"
            if self.invalid_json
            else json.dumps(
                {
                    "summary": "Evento oficial resumido.",
                    "risks": [],
                    "catalysts": [],
                    "contradictions": [],
                    "questions_for_senior_review": [],
                    "escalation_recommended": False,
                    "evidence_refs": self.refs,
                }
            )
        )
        return SimpleNamespace(
            model=self.model,
            content=content,
            thinking="reasoning",
            eval_count=self.eval_count,
            total_duration_ns=10,
        )


def test_evidence_fingerprint_is_order_independent():
    events = _events()
    assert evidence_fingerprint("PETR4", events) == evidence_fingerprint(
        "PETR4", list(reversed(events))
    )


def test_queue_is_idempotent_for_same_evidence_bundle(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    first = queue.enqueue("PETR4", _events())
    second = queue.enqueue("PETR4", list(reversed(_events())))

    assert first.queue_status == "ENQUEUED"
    assert second.queue_status == "ALREADY_QUEUED"
    assert first.request.analysis_id == second.request.analysis_id
    assert len(queue.pending()) == 1


def test_local_analyst_ready_dossier_is_reusable(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue("PETR4", _events()).request
    analyst = LocalEvidenceAnalyst(FakeClient())
    dossier = analyst.analyze(request)
    queue.complete(dossier)

    assert dossier.status == LocalAnalysisStatus.READY
    assert dossier.quality_flags == ()

    selection = LocalEvidenceContextSelector(queue).select(
        ticker="PETR4",
        evidence_events=_events(),
    )
    assert selection.status == "READY"
    assert selection.dossier is not None
    assert selection.dossier.analysis_id == request.analysis_id


def test_output_limit_marks_dossier_degraded_and_excludes_from_senior_context(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue("PETR4", _events()).request
    client = FakeClient(eval_count=256)
    dossier = LocalEvidenceAnalyst(client).analyze(request)
    queue.complete(dossier)

    assert dossier.status == LocalAnalysisStatus.DEGRADED
    assert "OUTPUT_LIMIT_REACHED" in dossier.quality_flags

    selection = LocalEvidenceContextSelector(queue).select(
        ticker="PETR4",
        evidence_events=_events(),
    )
    assert selection.status == "OMITTED"
    assert selection.dossier is None
    assert "OUTPUT_LIMIT_REACHED" in selection.reasons


def test_unknown_evidence_ref_marks_dossier_degraded(tmp_path):
    request = build_request("PETR4", _events())
    dossier = LocalEvidenceAnalyst(
        FakeClient(refs=["https://unknown.test/x"])
    ).analyze(request)

    assert dossier.status == LocalAnalysisStatus.DEGRADED
    assert "UNKNOWN_EVIDENCE_REF" in dossier.quality_flags


def test_changed_evidence_fingerprint_makes_old_dossier_stale(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue("PETR4", _events()).request
    dossier = LocalEvidenceAnalyst(FakeClient()).analyze(request)
    queue.complete(dossier)

    changed = _events() + [
        {
            "evidence_type": "official_disclosure",
            "evidence_id": "E3",
            "source_ref": "https://cvm.test/e3",
            "published_at": "2026-09-30T11:00:00+00:00",
            "headline": "Novo documento",
            "summary": "Novo fato",
            "materiality": "MATERIAL",
        }
    ]
    selection = LocalEvidenceContextSelector(queue).select(
        ticker="PETR4",
        evidence_events=changed,
    )

    assert selection.status == "OMITTED"
    assert "STALE_EVIDENCE" in selection.reasons


def test_senior_context_returns_immediately_without_local_dossier(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    builder = SeniorEvidenceContextBuilder(LocalEvidenceContextSelector(queue))

    context = builder.build(ticker="PETR4", evidence_events=_events())

    assert context.local_dossier is None
    assert context.local_dossier_status == "ABSENT"
    assert len(context.canonical_evidence) == 2


def test_senior_context_includes_only_current_ready_dossier(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue("PETR4", _events()).request
    dossier = LocalEvidenceAnalyst(FakeClient()).analyze(request)
    queue.complete(dossier)

    builder = SeniorEvidenceContextBuilder(LocalEvidenceContextSelector(queue))
    context = builder.build(ticker="PETR4", evidence_events=_events())

    assert context.local_dossier_status == "READY"
    assert context.local_dossier is not None
    assert context.local_dossier["status"] == "READY"


def test_stale_age_omits_dossier(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    request = queue.enqueue("PETR4", _events()).request
    old = LocalEvidenceDossier(
        analysis_id=request.analysis_id,
        ticker="PETR4",
        evidence_fingerprint=request.evidence_fingerprint,
        evidence_refs=request.source_refs,
        created_at=(datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        model="deepseek-r1:8b",
        prompt_version=request.prompt_version,
        status=LocalAnalysisStatus.READY,
        analysis={"summary": "old"},
    )
    queue.complete(old)

    selection = LocalEvidenceContextSelector(queue).select(
        ticker="PETR4",
        evidence_events=_events(),
    )
    assert selection.status == "OMITTED"
    assert "STALE_DOSSIER" in selection.reasons


def test_worker_processes_queue_and_persists_manifest(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    queue.enqueue("PETR4", _events())
    client = FakeClient()
    worker = LocalEvidenceAnalystJob(
        queue=queue,
        analyst=LocalEvidenceAnalyst(client),
    )

    result = worker.run(limit=5)

    assert result["processed"] == 1
    assert result["ready"] == 1
    assert result["failed"] == 0
    assert result["remaining_queue"] == 0
    assert client.calls == 1
    assert queue.latest("PETR4") is not None
    assert (queue.manifests_dir / "latest.json").is_file()


def test_default_local_analyst_uses_runtime_json_schema():
    analyst = LocalEvidenceAnalyst()
    assert analyst.client.format_schema == LOCAL_ANALYSIS_SCHEMA
    assert analyst.client.format_schema["additionalProperties"] is False
    assert "evidence_refs" in analyst.client.format_schema["required"]


class RuntimeFailingClient:
    model = "deepseek-r1:8b"
    num_predict = 256

    def ask(self, prompt):
        raise RuntimeError("Ollama request failed: temporary local model failure")


def test_dossier_runtime_failure_is_deferred_not_dropped(tmp_path):
    queue = LocalEvidenceQueue(tmp_path)
    queue.enqueue("PETR4", _events())
    worker = LocalEvidenceAnalystJob(
        queue=queue,
        analyst=LocalEvidenceAnalyst(RuntimeFailingClient()),
    )

    result = worker.run(limit=1)

    assert result["processed"] == 1
    assert result["deferred"] == 1
    assert result["failed"] == 0
    assert result["remaining_queue"] == 1
    assert result["results"][0]["status"] == "DEFERRED"
    assert "temporary local model failure" in result["results"][0]["error"]


def test_matching_dossier_survives_latest_pointer_for_another_evidence_topic(tmp_path):
    queue=LocalEvidenceQueue(tmp_path)
    news=build_request('ITUB4',_events())
    analyst=LocalEvidenceAnalyst(FakeClient())
    queue.complete(analyst.analyze(news))
    target=build_request('ITUB4',[{'evidence_type':'institution_price_target','source_ref':'https://cvm.test/e1','summary':'Separate target opinion'}])
    queue.complete(analyst.analyze(target))
    assert queue.latest('ITUB4').analysis_id==target.analysis_id
    selected=LocalEvidenceContextSelector(queue).select(ticker='ITUB4',evidence_events=_events())
    assert selected.status=='READY' and selected.dossier.analysis_id==news.analysis_id


def test_default_local_analyst_is_bounded_non_thinking_structured_extraction():
    analyst=LocalEvidenceAnalyst()
    assert analyst.client.think is False
    assert analyst.client.format_schema==LOCAL_ANALYSIS_SCHEMA
    assert build_request('ITUB4',_events()).prompt_version=='b3_local_evidence_analyst_v6'
    assert analyst.client.model == 'qwen3:4b-instruct-2507-q4_K_M'
    assert analyst.client.num_ctx == 4096
    assert analyst.client.num_predict == 2048
    assert analyst.client.timeout == 600
