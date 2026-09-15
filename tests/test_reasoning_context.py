from datetime import date
from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.orchestration.context import build_deterministic_context
from b3_agent.orchestration.workflow import build_workflow
from b3_agent.schemas.opportunity import Opportunity, OpportunityAssessment, OpportunitySet
from b3_agent.schemas.position import PortfolioContext, Position


class CapturingLLM:
    def __init__(self):
        self.context = None

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        import json

        self.context = json.loads(input_text)
        return {
            "action": "NO_CHANGE",
            "subject_id": "PETR4",
            "thesis": "Keep the current position while the supplied evidence remains valid.",
            "rationale": "Deterministic portfolio and opportunity facts were supplied for review.",
            "evidence_refs": ["obsidian:04_Stocks/PETR4.md"],
            "risks": ["Market conditions can change."],
            "opportunity_cost": "No immediate allocation change.",
            "capital_impact": "No immediate change.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Material deterioration in supplied evidence."],
        }


def test_deterministic_context_reaches_reasoning_without_mutation(tmp_path: Path):
    position = Position(
        position_id="pos-petr4",
        ticker="PETR4",
        instrument_type="STOCK",
        quantity=100.0,
        average_cost=30.0,
        market_price=35.0,
        market_value=3500.0,
        source_ref="BTG:Renda Variavel",
    )
    portfolio = PortfolioContext(
        as_of=date(2026, 9, 11),
        positions=(position,),
        cash=1000.0,
        source_refs=("BTG:Renda Variavel",),
        quality_status="VALIDATED",
    )
    opportunity = Opportunity(
        opportunity_id="opp-petr4-001",
        ticker="PETR4",
        instrument_type="STOCK",
        action="BUY",
        as_of=date(2026, 9, 11),
        expected_return=0.12,
        capital_requirement=3500.0,
        evidence_refs=("valuation:PETR4",),
        source_refs=("deterministic-test",),
        quality_status="VALIDATED",
        rationale="Golden opportunity for integration testing.",
    )
    assessment = OpportunityAssessment(
        opportunity_id=opportunity.opportunity_id,
        eligible=True,
        attractiveness="ATTRACTIVE",
        portfolio_fit="GOOD",
        ranking_evidence_refs=opportunity.evidence_refs,
        evidence_refs=opportunity.evidence_refs,
        ranking_key=(0, 0, 0, 0, -0.12, 0, 0, 0, opportunity.opportunity_id),
        rationale=opportunity.rationale,
    )
    opportunity_set = OpportunitySet(
        as_of=date(2026, 9, 11),
        ranked_opportunities=(assessment,),
        rejected_opportunities=(),
        ranking_policy_version="1.0",
        source_refs=("deterministic-test",),
        quality_status="VALIDATED",
    )

    context = build_deterministic_context(
        portfolio_context=portfolio,
        opportunity_set=opportunity_set,
    )

    assert context["portfolio"]["positions"][0]["ticker"] == "PETR4"
    assert context["portfolio"]["positions"][0]["quantity"] == 100.0
    assert context["portfolio"]["cash"] == 1000.0
    assert context["opportunities"]["quality_status"] == "VALIDATED"
    assert context["opportunities"]["ranked_opportunities"][0]["opportunity_id"] == "opp-petr4-001"
    assert context["opportunities"]["ranked_opportunities"][0]["attractiveness"] == "ATTRACTIVE"
    assert opportunity.action == "BUY"
    assert opportunity.expected_return == 0.12

    vault = tmp_path / "vault"
    (vault / "04_Stocks").mkdir(parents=True)
    (vault / "04_Stocks/PETR4.md").write_text(
        "# PETR4\n\nInvestment thesis and valuation policy.",
        encoding="utf-8",
    )
    llm = CapturingLLM()
    workflow = build_workflow(
        retriever=ObsidianRetriever(ObsidianKnowledgeStore(vault)),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    )
    result = workflow.invoke(
        {
            "request": "PETR4 investment thesis valuation",
            "deterministic_context": context,
        }
    )

    assert llm.context["deterministic_context"] == context
    assert result["proposal"]["subject_id"] == "PETR4"
    assert result["risk_validation"]["status"] == "PASS"
    assert result["status"] == "PASS"
