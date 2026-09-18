from __future__ import annotations

from b3_agent.mcp.orchestrator_server import analyze_b3
from b3_agent.orchestration.orchestrator import configure_workflow


class FakeWorkflow:
    def invoke(self, state):
        return {
            "status": "PASS",
            "decision_proposal": {"action": "NO_CHANGE"},
            "sources": ["BRAPI", "OPLAB"],
            "audit": [{"event": "validated"}],
        }


def test_analyze_b3_is_a_thin_transport_adapter() -> None:
    configure_workflow(FakeWorkflow())

    result = analyze_b3(
        "Analyze portfolio",
        "PETR4",
        {"portfolio_context": {"quality_status": "VALIDATED"}},
    )

    assert result == {
        "status": "PASS",
        "result": {
            "decision_proposal": {"action": "NO_CHANGE"},
        },
        "sources": ["BRAPI", "OPLAB"],
        "audit": [{"event": "validated"}],
        "error": None,
    }
