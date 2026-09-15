from datetime import date
from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.orchestration.context import build_deterministic_context
from b3_agent.orchestration.workflow import build_workflow
from b3_agent.schemas.opportunity import Opportunity, OpportunitySet, OpportunityAssessment
from b3_agent.schemas.position import PortfolioContext, Position


class RealOpportunityFakeLLM:
    def __init__(self):
        self.context = None

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        import json
        self.context = json.loads(input_text)
        return {
            "action": "BUY",
            "subject_id": "PETR4",
            "thesis": "The deterministic opportunity is eligible and should be reviewed for purchase.",
            "rationale": "Reasoning is based on the supplied OpportunitySet and portfolio facts.",
            "evidence_refs": ["valuation:PETR4", "obsidian:04_Stocks/PETR4.md"],
            "risks": ["Market conditions can change."],
            "opportunity_cost": "Capital would be allocated away from other opportunities.",
            "capital_impact": "Requires the deterministic capital requirement.",
            "confidence": "MEDIUM",
            "invalidation_conditions": ["Opportunity becomes ineligible or data quality deteriorates."],
        }


def test_real_deterministic_opportunity_reaches_reasoning_and_risk_gate(tmp_path: Path):
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
        cash=10000.0,
        source_refs=("BTG:Renda Variavel",),
        quality_status="VALIDATED",
    )
    opportunity = Opportunity(
        opportunity_id="opp-petr4-real-001",
        ticker="PETR4",
        instrument_type="STOCK",
        action="BUY",
        as_of=date(2026, 9, 11),
        expected_return=0.12,
        capital_requirement=3500.0,
        evidence_refs=("valuation:PETR4",),
        source_refs=("deterministic-engine",),
        quality_status="VALIDATED",
        rationale="Eligible deterministic opportunity.",
    )
    assessment = OpportunityAssessment(
        opportunity_id=opportunity.opportunity_id,
        eligible=True,
        attractiveness="ATTRACTIVE",
        portfolio_fit="GOOD",
        ranking_key=(0, 0, 0, 0, -0.12, 0, 0, 0, opportunity.opportunity_id),
        evidence_refs=opportunity.evidence_refs,
        rationale=opportunity.rationale,
    )
    opportunity_set = OpportunitySet(
        as_of=date(2026, 9, 11),
        ranked_opportunities=(assessment,),
        rejected_opportunities=(),
        ranking_policy_version="1.0",
        source_refs=("deterministic-engine",),
        quality_status="VALIDATED",
    )

    context = build_deterministic_context(
        portfolio_context=portfolio,
        opportunity_set=opportunity_set,
    )

    vault = tmp_path / "vault"
    (vault / "04_Stocks").mkdir(parents=True)
    (vault / "04_Stocks/PETR4.md").write_text(
        "# PETR4\n\nInvestment thesis and valuation policy.",
        encoding="utf-8",
    )
    llm = RealOpportunityFakeLLM()
    workflow = build_workflow(
        retriever=ObsidianRetriever(ObsidianKnowledgeStore(vault)),
        reasoning_agent=InvestmentReasoningAgent(llm),
        risk_validator=RiskValidator(),
    )

    result = workflow.invoke({
        "request": "Review PETR4 opportunity",
        "deterministic_context": context,
    })

    assert llm.context["deterministic_context"]["opportunities"]["ranked_opportunities"][0]["opportunity_id"] == "opp-petr4-real-001"
    assert llm.context["deterministic_context"]["opportunities"]["ranked_opportunities"][0]["eligible"] is True
    assert result["proposal"]["action"] == "BUY"
    assert result["risk_validation"]["status"] == "PASS"
    assert result["status"] == "PASS"
