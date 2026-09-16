from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import MarketAnalysisAgent, OptionsAnalysisAgent, PortfolioAnalysisAgent
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.orchestration.workflow import build_workflow


class FakeLLM:
    def __init__(self):
        self.calls = []

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        self.calls.append({"schema_name": schema_name, "input_text": input_text})
        if schema_name.endswith("_analysis"):
            return {
                "summary": f"{schema_name} reviewed.",
                "findings": ["Facts were supplied upstream."],
                "risks": ["Conditions may change."],
                "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
                "source_refs": ["test:source"],
            }
        if schema_name == "investment_synthesis":
            return {
                "summary": "Specialists are broadly aligned.",
                "agreements": ["The supplied evidence is internally consistent."],
                "conflicts": [],
                "uncertainties": ["Future market conditions can change."],
                "evidence_gaps": [],
                "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
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
    (vault / "04_Stocks").mkdir(parents=True)
    (vault / "04_Stocks/PETR4.md").write_text(
        "# PETR4\n\nInvestment thesis and valuation policy.", encoding="utf-8"
    )
    llm = FakeLLM()
    workflow = build_workflow(
        retriever=ObsidianRetriever(ObsidianKnowledgeStore(vault)),
        market_agent=MarketAnalysisAgent(llm),
        portfolio_agent=PortfolioAnalysisAgent(llm),
        options_agent=OptionsAnalysisAgent(llm),
        synthesis_agent=SynthesisAgent(llm),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    )

    result = workflow.invoke({
        "user_question": "PETR4 investment thesis valuation",
        "portfolio_context": {"quality_status": "VALIDATED"},
        "market_analysis": {"deterministic": "market-fact"},
        "options_analysis": {"deterministic": "options-fact"},
        "risk_analysis": {"deterministic": "risk-fact"},
        "signals": [{"name": "signal-1"}],
        "threats": [{"name": "threat-1"}],
    })

    assert result["evidence"]
    assert result["market_analysis"] == {"deterministic": "market-fact"}
    assert result["options_analysis"] == {"deterministic": "options-fact"}
    assert result["market_agent_analysis"]["agent"] == "market_analysis"
    assert result["portfolio_agent_analysis"]["agent"] == "portfolio_analysis"
    assert result["options_agent_analysis"]["agent"] == "options_analysis"
    assert result["synthesis"]["summary"] == "Specialists are broadly aligned."
    assert result["decision_proposal"]["action"] == "NO_CHANGE"
    assert result["risk_validation"]["status"] == "PASS"
    assert result["status"] == "PASS"

    names = {call["schema_name"] for call in llm.calls}
    assert {
        "market_analysis_analysis",
        "portfolio_analysis_analysis",
        "options_analysis_analysis",
        "investment_synthesis",
        "investment_decision",
    } == names
    synthesis_input = next(call["input_text"] for call in llm.calls if call["schema_name"] == "investment_synthesis")
    assert '"market_agent_analysis"' in synthesis_input
    assert '"portfolio_agent_analysis"' in synthesis_input
    assert '"options_agent_analysis"' in synthesis_input
    assert '"market-fact"' in synthesis_input

    decision_input = next(call["input_text"] for call in llm.calls if call["schema_name"] == "investment_decision")
    assert '"synthesis"' in decision_input
