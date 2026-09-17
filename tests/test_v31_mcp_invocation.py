from __future__ import annotations

from b3_agent.mcp.server import mcp
from b3_agent.orchestration.orchestrator import configure_workflow


class FakeWorkflow:
    def invoke(self, state):
        assert state["user_question"] == "Analyze PETR4 covered-call opportunity"
        assert state["ticker"] == "PETR4"
        assert state["portfolio_context"]["quality_status"] == "VALIDATED"
        return {
            "status": "PASS",
            "decision_proposal": {"action": "NO_CHANGE"},
            "sources": ["BRAPI", "OPLAB"],
            "audit": [{"event": "validated"}],
        }


def test_mcp_registered_tool_invocation_reaches_v31_orchestrator() -> None:
    configure_workflow(FakeWorkflow())

    tool = mcp._tool_manager.get_tool("analyze_portfolio")
    result = tool.fn(
        task="Analyze PETR4 covered-call opportunity",
        ticker="petr4",
        context={"portfolio_context": {"quality_status": "VALIDATED"}},
    )

    assert result == {
        "status": "PASS",
        "result": {"decision_proposal": {"action": "NO_CHANGE"}},
        "sources": ["BRAPI", "OPLAB"],
        "audit": [{"event": "validated"}],
        "error": None,
    }
