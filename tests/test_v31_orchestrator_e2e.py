from __future__ import annotations

from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.orchestration.orchestrator import b3_orchestrator, configure_workflow
from b3_agent.orchestration.workflow import build_workflow


class FakeLLM:
    def complete_json(self, *, instructions, input_text, schema_name, schema):
        return {
            "action": "NO_CHANGE",
            "subject_id": "PETR4",
            "thesis": "Maintain the current thesis while supplied evidence remains valid.",
            "rationale": "The deterministic context and retrieved investor evidence support no immediate change.",
            "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
            "risks": ["Market conditions can change."],
            "opportunity_cost": "No immediate allocation change.",
            "capital_impact": "No immediate change.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Material deterioration in supplied evidence."],
        }


def test_v31_orchestrator_end_to_end_through_langgraph_and_obsidian(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "04_Stocks").mkdir(parents=True)
    (vault / "04_Stocks/PETR4.md").write_text(
        "# PETR4\n\nInvestment thesis and valuation policy.",
        encoding="utf-8",
    )

    workflow = build_workflow(
        retriever=ObsidianRetriever(ObsidianKnowledgeStore(vault)),
        reasoning_agent=InvestmentReasoningAgent(FakeLLM()),
        risk_validator=RiskValidator(),
    )
    configure_workflow(workflow)

    response = b3_orchestrator(
        "PETR4 investment thesis valuation",
        "PETR4",
        {
            "portfolio_context": {"quality_status": "VALIDATED"},
            "opportunities": [{"opportunity_id": "OP-001", "ticker": "PETR4"}],
            "sources": ["BTG", "deterministic-test"],
        },
    )

    assert response.status == "PASS"
    assert response.result["user_question"] == "PETR4 investment thesis valuation"
    assert response.result["ticker"] == "PETR4"
    assert response.result["evidence"][0]["source_ref"] == "obsidian:04_Stocks/PETR4.md"
    assert response.result["decision_proposal"]["action"] == "NO_CHANGE"
    assert response.result["risk_validation"]["status"] == "PASS"
    assert response.sources == ("BTG", "deterministic-test")
