from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import (
    MarketAnalysisAgent,
    OptionsAnalysisAgent,
    PortfolioAnalysisAgent,
)
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.orchestration.workflow import build_workflow


class FakeLLM:
    def __init__(self):
        self.calls = []

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        self.calls.append({"schema_name": schema_name, "input_text": input_text})
        if schema_name == "market_analysis_analysis":
            return {
                "summary": "Market slice reviewed.",
                "findings": ["Market facts were supplied upstream."],
                "risks": ["Market conditions may change."],
                "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
                "source_refs": ["market:test"],
            }
        if schema_name == "portfolio_analysis_analysis":
            return {
                "summary": "Portfolio slice reviewed.",
                "findings": ["Portfolio facts were supplied upstream."],
                "risks": ["Position exposure may change."],
                "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
                "source_refs": ["portfolio:test"],
            }
        if schema_name == "options_analysis_analysis":
            return {
                "summary": "Options slice reviewed.",
                "findings": ["Option opportunities were supplied upstream."],
                "risks": ["Option lifecycle conditions may change."],
                "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
                "source_refs": ["options:test"],
            }
        return {
            "action": "NO_CHANGE",
            "subject_id": "PETR4",
            "thesis": "Maintain the current thesis while evidence remains supportive.",
            "rationale": "Specialist analyses and deterministic context do not require a change.",
            "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
            "risks": ["Market conditions can change."],
            "opportunity_cost": "Capital remains allocated to the current position.",
            "capital_impact": "No immediate change.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Material deterioration in the supplied evidence."],
        }


def test_full_specialist_path_preserves_deterministic_analysis(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "04_Stocks").mkdir()
    (vault / "04_Stocks/PETR4.md").write_text(
        "# PETR4\n\nInvestment thesis and valuation policy.",
        encoding="utf-8",
    )
    store = ObsidianKnowledgeStore(vault)
    retriever = ObsidianRetriever(store)
    llm = FakeLLM()

    workflow = build_workflow(
        retriever=retriever,
        market_agent=MarketAnalysisAgent(llm),
        portfolio_agent=PortfolioAnalysisAgent(llm),
        options_agent=OptionsAnalysisAgent(llm),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    )
    result = workflow.invoke(
        {
            "user_question": "PETR4 investment thesis valuation",
            "portfolio_context": {"quality_status": "VALIDATED"},
            "market_analysis": {"deterministic": "market-fact"},
            "options_analysis": {"deterministic": "options-fact"},
            "risk_analysis": {"deterministic": "risk-fact"},
            "signals": [{"name": "signal-1"}],
            "threats": [{"name": "threat-1"}],
        }
    )

    assert result["evidence"]
    assert result["market_analysis"] == {"deterministic": "market-fact"}
    assert result["options_analysis"] == {"deterministic": "options-fact"}
    assert result["market_agent_analysis"]["agent"] == "market_analysis"
    assert result["portfolio_agent_analysis"]["agent"] == "portfolio_analysis"
    assert result["options_agent_analysis"]["agent"] == "options_analysis"
    assert result["decision_proposal"]["action"] == "NO_CHANGE"
    assert result["risk_validation"]["status"] == "PASS"
    assert result["status"] == "PASS"

    names = [call["schema_name"] for call in llm.calls]
    assert names == [
        "market_analysis_analysis",
        "portfolio_analysis_analysis",
        "options_analysis_analysis",
        "decision_proposal",
    ]
    synthesis_input = llm.calls[-1]["input_text"]
    assert "market_agent_analysis" in synthesis_input
    assert "portfolio_agent_analysis" in synthesis_input
    assert "options_agent_analysis" in synthesis_input
