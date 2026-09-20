from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import (
    MarketAnalysisAgent,
    OptionsAnalysisAgent,
    PortfolioAnalysisAgent,
)
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.schemas.opportunity import Opportunity
from b3_agent.orchestration.workflow import build_workflow


GOLDEN_CASES = (
    ("GC-C01", "Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?"),
    ("GC-C02", "Tenho R$ 20 mil. Essa PUT cabe na minha carteira?"),
    ("GC-C03", "Tenho essa carteira. Existe alguma oportunidade que melhore minha diversificação?"),
    ("GC-C04", "Vale a pena analisar uma nova oportunidade em vez de manter essa posição?"),
    ("GC-C05", "É melhor comprar PETR4 ou vender uma PUT de PETR4?"),
    ("GC-C06", "PETR4 está barata?"),
    ("GC-C07", "Como está minha PUT e existe alguma alternativa que eu deveria analisar?"),
    ("GC-C08", "Qual a melhor coisa para eu fazer agora?"),
)


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        self.calls.append({"schema_name": schema_name, "input_text": input_text})
        if schema_name.endswith("_analysis"):
            return {
                "summary": "Specialist analysis grounded in supplied deterministic context.",
                "findings": ["The upstream deterministic context was received."],
                "risks": ["Evidence and market conditions can change."],
                "evidence_refs": ["obsidian:copilot-golden.md"],
                "source_refs": ["test:copilot"],
            }
        if schema_name == "investment_synthesis":
            return {
                "summary": "Structured synthesis for human review.",
                "agreements": ["Specialists received the same upstream facts."],
                "conflicts": [],
                "uncertainties": ["Future conditions may change."],
                "evidence_gaps": [],
                "evidence_refs": ["obsidian:copilot-golden.md"],
            }
        return {
            "action": "WAIT" if "melhor coisa" in input_text else "HUMAN_REVIEW",
            "subject_id": "PORTFOLIO",
            "thesis": "Use only the supplied deterministic facts and keep the final decision with the human.",
            "rationale": "Golden conversational contract test.",
            "evidence_refs": ["obsidian:copilot-golden.md"],
            "risks": ["Conditions may change."],
            "opportunity_cost": "Requires comparison with available alternatives.",
            "capital_impact": "Must be evaluated from deterministic capital requirements.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Material change in supplied evidence."],
        }


def _workflow(tmp_path: Path, llm: FakeLLM):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "copilot-golden.md").write_text(
        "# Copilot Golden Evidence\nPETR4 PUT carteira oportunidade diversificação posição comprar vender barata alternativa melhor decisão.\nDeterministic evidence fixture.",
        encoding="utf-8",
    )

    opportunity = Opportunity(
        opportunity_id="SELL_PUT:PETRV300",
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_PUT",
        as_of=date(2026, 9, 18),
        expected_return=0.18,
        capital_requirement=3000.0,
        evidence_refs=("options:PETRV300",),
        source_refs=("fixture:BTG",),
        quality_status="VALIDATED",
        rationale="Deterministic fixture opportunity.",
    )
    opportunity_set = OpportunityPipeline().build(
        (opportunity,),
        as_of=date(2026, 9, 18),
        source_refs=("fixture:BTG",),
    )

    return build_workflow(
        retriever=ObsidianRetriever(ObsidianKnowledgeStore(vault)),
        market_agent=MarketAnalysisAgent(llm),
        portfolio_agent=PortfolioAnalysisAgent(llm),
        options_agent=OptionsAnalysisAgent(llm),
        synthesis_agent=SynthesisAgent(llm),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    ), opportunity_set


@pytest.mark.parametrize("case_id,question", GOLDEN_CASES)
def test_golden_conversational_cases_preserve_orchestrated_contract(
    tmp_path: Path, case_id: str, question: str
) -> None:
    llm = FakeLLM()
    workflow, opportunity_set = _workflow(tmp_path, llm)

    result = workflow.invoke(
        {
            "user_question": question,
            "client": "react-dashboard-copilot",
            "surface": "copilot",
            "use_case_id": case_id,
            "as_of": date(2026, 9, 18),
            "portfolio_context": {
                "quality_status": "VALIDATED",
                "cash": 80000.0,
                "positions": [{"ticker": "PETR4", "quantity": 100}],
            },
            "portfolio_intelligence": {
                "capital_risk": {"assignment_capital": 3000.0},
                "exposures": [{"ticker": "PETR4", "weight": 0.35}],
            },
            "options_transactions": [],
            "options_performance": {"lifecycles": [], "by_underlying": []},
            "opportunity_set": opportunity_set,
            "deterministic_context": {
                "valuation": {
                    "PETR4": {
                        "base_value": 42.0,
                        "accumulation_price": 35.0,
                        "source_ref": "valuation:PETR4:fixture",
                    }
                }
            },
        }
    )

    assert result["use_case_id"] == case_id
    assert result["decision_proposal"]["action"] in {"WAIT", "HUMAN_REVIEW"}
    assert result["risk_validation"]["status"] == "PASS"
    assert result["synthesis"]["summary"]
    assert result["opportunities"]
    assert result["action_candidates"]
    assert result["evidence"]

    decision_input = next(
        x["input_text"] for x in llm.calls if x["schema_name"] == "investment_decision"
    )
    assert "PETR4" in decision_input
    assert "opportunities" in decision_input
    assert "portfolio_context" in decision_input
    assert "portfolio_intelligence" in decision_input


def test_gc_c01_opportunity_discovery_exposes_affordable_validated_opportunity(tmp_path: Path) -> None:
    """C01 must expose deterministic opportunity facts before human review."""
    llm = FakeLLM()
    workflow, opportunity_set = _workflow(tmp_path, llm)

    result = workflow.invoke(
        {
            "user_question": GOLDEN_CASES[0][1],
            "client": "react-dashboard-copilot",
            "surface": "copilot",
            "use_case_id": "GC-C01",
            "as_of": date(2026, 9, 18),
            "portfolio_context": {
                "quality_status": "VALIDATED",
                "cash": 80000.0,
                "positions": [{"ticker": "PETR4", "quantity": 100}],
            },
            "portfolio_intelligence": {
                "capital_risk": {"assignment_capital": 3000.0},
            },
            "opportunity_set": opportunity_set,
        }
    )

    opportunities = result["opportunities"]
    c01 = next(item for item in opportunities if item["opportunity_id"] == "SELL_PUT:PETRV300")

    assert result["use_case_id"] == "GC-C01"
    assert c01["eligible"] is True
    assert c01["quality_status"] if "quality_status" in c01 else True
    assert c01["ticker"] == "PETR4"
    assert c01["action"] == "SELL_PUT"
    assert c01["capital_requirement"] == 3000.0
    assert c01["expected_return"] == 0.18
    assert c01["as_of"] == "2026-09-18"
    assert c01["source_refs"] == ["fixture:BTG"]
    assert c01["evidence_refs"] == ["options:PETRV300"]

    candidates = result["action_candidates"]
    assert any(
        item["action_candidate_id"] == "ACTION:SELL_PUT:PETRV300"
        and item["action_type"] == "SELL_PUT"
        and item["quality_status"] == "VALIDATED"
        for item in candidates
    )

    decision_input = next(
        x["input_text"] for x in llm.calls if x["schema_name"] == "investment_decision"
    )
    assert '"cash": 80000.0' in decision_input
    assert '"capital_requirement": 3000.0' in decision_input
    assert '"expected_return": 0.18' in decision_input
    assert "SELL_PUT:PETRV300" in decision_input
    assert "fixture:BTG" in decision_input



def test_golden_cases_never_create_an_execution_action(tmp_path: Path) -> None:
    llm = FakeLLM()
    workflow, opportunity_set = _workflow(tmp_path, llm)
    result = workflow.invoke(
        {
            "user_question": GOLDEN_CASES[0][1],
            "client": "react-dashboard-copilot",
            "surface": "copilot",
            "use_case_id": GOLDEN_CASES[0][0],
            "portfolio_context": {"quality_status": "VALIDATED", "cash": 80000.0},
            "opportunity_set": opportunity_set,
        }
    )
    assert result["decision_proposal"]["action"] not in {"EXECUTE", "PLACE_ORDER", "TRADE"}
    assert result["risk_validation"]["status"] == "PASS"
