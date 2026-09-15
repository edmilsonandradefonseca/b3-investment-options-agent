from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.orchestration.workflow import build_workflow


class FakeLLM:
    def complete_json(self, *, instructions, input_text, schema_name, schema):
        return {
            "action": "NO_CHANGE",
            "subject_id": "PETR4",
            "thesis": "Maintain the current thesis while evidence remains supportive.",
            "rationale": "The supplied deterministic context and investor notes do not require a change.",
            "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
            "risks": ["Market conditions can change."],
            "opportunity_cost": "Capital remains allocated to the current position.",
            "capital_impact": "No immediate change.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Material deterioration in the supplied evidence."],
        }


def test_mvp_workflow_retrieves_obsidian_and_validates(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "04_Stocks").mkdir()
    (vault / "04_Stocks/PETR4.md").write_text(
        "# PETR4\n\nInvestment thesis and valuation policy.",
        encoding="utf-8",
    )

    store = ObsidianKnowledgeStore(vault)
    retriever = ObsidianRetriever(store)
    workflow = build_workflow(
        retriever=retriever,
        reasoning_agent=InvestmentReasoningAgent(FakeLLM()),
        risk_validator=RiskValidator(),
    )

    result = workflow.invoke(
        {
            "request": "PETR4 investment thesis valuation",
            "deterministic_context": {"quality_status": "VALIDATED"},
        }
    )

    assert result["evidence"]
    assert result["evidence"][0]["source_ref"] == "obsidian:04_Stocks/PETR4.md"
    assert result["proposal"]["action"] == "NO_CHANGE"
    assert result["risk_validation"]["status"] == "PASS"
    assert result["status"] == "PASS"
