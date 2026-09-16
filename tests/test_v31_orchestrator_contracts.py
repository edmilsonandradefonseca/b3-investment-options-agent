from __future__ import annotations

import pytest

from b3_agent.orchestration.contracts import (
    B3State,
    OrchestratorRequest,
    OrchestratorResponse,
)
from b3_agent.orchestration.orchestrator import (
    b3_orchestrator,
    configure_workflow,
)


class FakeWorkflow:
    def __init__(self) -> None:
        self.received: B3State | None = None

    def invoke(self, state: B3State) -> dict:
        self.received = state
        return {
            "status": "PASS",
            "opportunities": [{"opportunity_id": "OP-001"}],
            "sources": ["BRAPI"],
            "audit": [{"event": "workflow_completed"}],
        }


def test_orchestrator_request_normalizes_public_inputs() -> None:
    request = OrchestratorRequest.from_inputs(
        "  analyze portfolio  ",
        " itub4 ",
        {"portfolio_context": {"as_of": "2026-09-11"}},
    )

    assert request.task == "analyze portfolio"
    assert request.ticker == "ITUB4"
    assert request.context == {"portfolio_context": {"as_of": "2026-09-11"}}


def test_orchestrator_request_rejects_empty_task() -> None:
    with pytest.raises(ValueError, match="task must not be empty"):
        OrchestratorRequest.from_inputs("   ")


def test_orchestrator_response_normalizes_status_and_is_immutable() -> None:
    response = OrchestratorResponse(
        status=" pass ",
        result={"value": 1},
        sources=["BRAPI"],
        audit=[{"event": "done"}],
    )

    assert response.status == "PASS"
    assert response.sources == ("BRAPI",)
    assert response.audit == ({"event": "done"},)


def test_b3_orchestrator_is_single_logical_workflow_entry_point() -> None:
    workflow = FakeWorkflow()
    configure_workflow(workflow)

    response = b3_orchestrator(
        "Find opportunities",
        "ITUB4",
        {"portfolio_context": {"as_of": "2026-09-11"}},
    )

    assert workflow.received == {
        "user_question": "Find opportunities",
        "ticker": "ITUB4",
        "portfolio_context": {"as_of": "2026-09-11"},
    }
    assert response.status == "PASS"
    assert response.result["opportunities"] == [{"opportunity_id": "OP-001"}]
    assert response.sources == ("BRAPI",)
    assert response.audit == ({"event": "workflow_completed"},)


def test_b3_orchestrator_requires_runtime_workflow_configuration() -> None:
    configure_workflow(None)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="workflow is not configured"):
        b3_orchestrator("Analyze portfolio")
