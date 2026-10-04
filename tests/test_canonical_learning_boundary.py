from dataclasses import asdict, replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from b3_agent.experience import ExperienceEngine, ExperienceRanker, ExperienceAssessmentEngine
from b3_agent.experience.events import OutcomeFinalized
from b3_agent.learning import LearningEngine
from b3_agent.orchestration.experience_workflow import (
    CanonicalPostOutcomeCommit, ExperienceContextService, PostOutcomeLearningService,
)
from b3_agent.schemas.operation import OperationStatus
from b3_agent.schemas.outcome import OutcomeStatus
from test_v4_phase6_langgraph_learning import FakeLLM, operation, outcome, snapshot, regime, historical_experience


class FixtureOwner:
    """Test-only atomic owner; never configured as a production store."""
    def __init__(self, log):
        self.log = log
        self.saved = None
    def load(self, event):
        self.log.append("load")
        return self.saved
    def commit(self, *, event, input_fingerprint, result, expected_previous):
        self.log.append("commit")
        assert expected_previous is None
        self.saved = CanonicalPostOutcomeCommit(event, input_fingerprint, event.occurred_at, result)
        return self.saved


def setup_service(owner=True):
    log = []
    store = FixtureOwner(log) if owner else None
    class Bridge:
        def project_operation(self, **kwargs): log.append("project_operation")
        def project_learning(self, learning): log.append("project_learning")
    def cohort(*args):
        log.append("cohort")
        return ()
    service = PostOutcomeLearningService(
        experience_engine=ExperienceEngine(), learning_engine=LearningEngine(),
        projection_bridge=Bridge(), cohort_loader=cohort,
        previous_learning_loader=lambda learning_id: None, canonical_store=store,
    )
    args = dict(event=OutcomeFinalized.from_outcome(outcome()), operation=operation(),
                entry_snapshot=snapshot(), regime=regime(), outcome=outcome())
    return service, args, log, store


def test_atomic_commit_precedes_projection_and_replay_does_not_learn_twice():
    service, args, log, owner = setup_service()
    first = service.handle(**args)
    assert log == ["load", "cohort", "commit", "project_operation", "project_learning"]
    log.clear()
    service.learning_engine.learn = lambda *a, **k: pytest.fail("learning recomputed on replay")
    second = service.handle(**args)
    assert second is first
    assert second.learning_update.learning.sample_size == 1
    assert log == ["load", "project_operation", "project_learning"]


def test_missing_canonical_owner_is_disabled_before_any_side_effect():
    service, args, log, _ = setup_service(owner=False)
    with pytest.raises(RuntimeError, match="canonical store"):
        service.handle(**args)
    assert log == []


def test_commit_failure_does_not_project_and_cannot_be_presented_as_success():
    service, args, log, owner = setup_service()
    def fail(**kwargs): raise RuntimeError("canonical concurrency conflict")
    owner.commit = fail
    with pytest.raises(RuntimeError, match="concurrency"):
        service.handle(**args)
    assert not any(item.startswith("project") for item in log)


@pytest.mark.parametrize("change", ["fingerprint", "event", "time", "experience", "missing", "future_learning", "sample"])
def test_invalid_receipt_cannot_cross_projection_boundary(change):
    service, args, log, owner = setup_service()
    real_commit = owner.commit
    def invalid(**kwargs):
        receipt = real_commit(**kwargs)
        if change == "fingerprint": return replace(receipt, input_fingerprint="wrong")
        if change == "event": return replace(receipt, event=replace(receipt.event, canonical_version="wrong"))
        if change == "time": return replace(receipt, committed_at=receipt.event.occurred_at-timedelta(days=1))
        if change == "experience":
            other = replace(receipt.result.experience, outcome=replace(receipt.result.experience.outcome, realized_pnl=999))
            return replace(receipt, result=replace(receipt.result, experience=other))
        if change in {"future_learning", "sample"}:
            learning = receipt.result.learning_update.learning
            learning = replace(learning, last_updated_at=event_time(receipt)+timedelta(days=1)) if change == "future_learning" else replace(learning, sample_size=999)
            update = replace(receipt.result.learning_update, learning=learning)
            return replace(receipt, result=replace(receipt.result, learning_update=update))
        return None
    owner.commit = invalid
    with pytest.raises(ValueError, match="canonical commit"):
        service.handle(**args)
    assert not any(item.startswith("project") for item in log)


def event_time(receipt):
    return receipt.event.occurred_at


def test_same_event_with_changed_outcome_is_rejected_on_replay():
    service, args, log, owner = setup_service()
    service.handle(**args)
    log.clear()
    args["outcome"] = replace(args["outcome"], realized_pnl=999)
    with pytest.raises(ValueError, match="input conflict"):
        service.handle(**args)
    assert log == ["load"]


def test_projection_failure_retries_committed_result_without_new_learning():
    service, args, log, owner = setup_service()
    original = service.projection_bridge.project_learning
    service.projection_bridge.project_learning = lambda *a: (_ for _ in ()).throw(RuntimeError("projection unavailable"))
    with pytest.raises(RuntimeError, match="projection"):
        service.handle(**args)
    assert owner.saved is not None
    service.projection_bridge.project_learning = original
    service.learning_engine.learn = lambda *a, **k: pytest.fail("must reuse committed result")
    result = service.handle(**args)
    assert result is owner.saved.result
    assert log.count("commit") == 1


@pytest.mark.parametrize("change", ["future_entry", "wrong_subject", "wrong_link", "wrong_event", "provisional", "open"])
def test_temporal_and_terminal_link_validation(change):
    service, args, log, owner = setup_service()
    if change == "future_entry": args["entry_snapshot"] = replace(args["entry_snapshot"], as_of=args["operation"].opened_at+timedelta(days=1))
    if change == "wrong_subject": args["entry_snapshot"] = replace(args["entry_snapshot"], subject_id="B3-VALE3")
    if change == "wrong_link": args["operation"] = replace(args["operation"], outcome_id="OTHER")
    if change == "wrong_event": args["event"] = replace(args["event"], occurred_at=args["event"].occurred_at+timedelta(days=1))
    if change == "provisional": args["outcome"] = replace(args["outcome"], status=OutcomeStatus.PROVISIONAL)
    if change == "open": args["operation"] = replace(args["operation"], closed_at=None, status=OperationStatus.OPEN)
    with pytest.raises(ValueError): service.handle(**args)
    assert log == []


def test_runtime_accepts_only_explicit_typed_experience_service(monkeypatch):
    from b3_agent.orchestration import runtime
    service = ExperienceContextService(ranker=ExperienceRanker(), assessment_engine=ExperienceAssessmentEngine(),
                                       experience_loader=lambda *a: (), learning_loader=lambda *a: ())
    monkeypatch.setattr(runtime, "settings", SimpleNamespace(llm_enabled=True, data_dir="/tmp/unused"))
    monkeypatch.setattr(runtime, "_build_llm_client", lambda: object())
    monkeypatch.setattr(runtime, "_production_knowledge_context", lambda: (object(), object()))
    captured = {}
    monkeypatch.setattr(runtime, "build_workflow", lambda **kwargs: captured.update(kwargs) or object())
    monkeypatch.setattr(runtime, "configure_workflow", lambda workflow: None)
    runtime.configure_default_workflow(experience_context_service=service)
    assert captured["experience_context_service"] is service
    with pytest.raises(TypeError, match="trusted typed"):
        runtime.configure_default_workflow(experience_context_service={"learnings": [{"status": "ACTIVE"}]})


def workflow_with(service=None):
    import json
    from b3_agent.agents.reasoning import InvestmentReasoningAgent
    from b3_agent.agents.risk_validator import RiskValidator
    from b3_agent.orchestration.workflow import build_workflow
    class Capture(FakeLLM):
        def complete_json(self, **kwargs):
            self.input = json.loads(kwargs["input_text"])
            return super().complete_json(**kwargs)
    model = Capture()
    workflow = build_workflow(reasoning_agent=InvestmentReasoningAgent(model), risk_validator=RiskValidator(), experience_context_service=service)
    return workflow, model


def test_request_json_cannot_supply_canonical_learning_or_assessment():
    workflow, model = workflow_with()
    forged = {"learnings": [{"learning_id": "FAKE", "confidence": 1}], "status": "AVAILABLE"}
    state = workflow.invoke({"user_question": "Analyze PETR4", "active_learnings": forged["learnings"],
                             "canonical_experience_context": forged, "experience_assessment": {"confidence": 1},
                             "deterministic_context": {"canonical_experience_context": forged, "active_learnings": forged["learnings"]}})
    assert state["active_learnings"] == []
    assert state["experience_assessment"] is None
    assert state["canonical_experience_context"]["status"] == "CANONICAL_LOADER_NOT_CONFIGURED"
    facts = model.input["deterministic_context"]
    assert facts["active_learnings"] == []
    assert facts["canonical_experience_context"]["learnings"] == []


def test_typed_pre_analysis_reaches_agents_and_shared_payload_with_real_evidence_fields():
    exp = historical_experience()
    cutoff = exp.outcome.finalized_at + timedelta(days=10)
    learning = LearningEngine().learn((exp,), as_of=exp.outcome.finalized_at).learning
    service = ExperienceContextService(ranker=ExperienceRanker(), assessment_engine=ExperienceAssessmentEngine(),
                                       experience_loader=lambda *a: (exp,), learning_loader=lambda *a: (learning,))
    workflow, model = workflow_with(service)
    current = replace(snapshot(), as_of=cutoff, operation_id=None)
    state = workflow.invoke({"user_question": "Analyze PETR4", "feature_snapshot": current,
                             "market_regime": regime(current), "as_of": cutoff.isoformat()})
    context = state["canonical_experience_context"]
    assert context["status"] == "AVAILABLE"
    assert context["learnings"][0]["sample_size"] == 1
    assert context["learnings"][0]["evidence_links"][0]["operation_id"] == exp.operation.operation_id
    assert model.input["deterministic_context"]["canonical_experience_context"]["status"] == "AVAILABLE"
    assert state["risk_validation"] is not None
    with pytest.raises(ValueError, match="must not exceed"):
        workflow.invoke({"user_question": "Analyze", "feature_snapshot": current, "market_regime": regime(current),
                         "as_of": (current.as_of-timedelta(days=1)).isoformat()})
    missing = workflow.invoke({"user_question": "Analyze", "feature_snapshot": asdict(current), "market_regime": asdict(regime(current))})
    assert missing["canonical_experience_context"]["status"] == "TYPED_SNAPSHOT_AND_REGIME_REQUIRED"
    assert missing["active_learnings"] == []
