from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.agents.specialist import MarketAnalysisAgent, OptionsAnalysisAgent, PortfolioAnalysisAgent
from b3_agent.agents.synthesis import SynthesisAgent
from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.context import AgentContext
from b3_agent.schemas.opportunity import (
    ActionCandidate,
    Opportunity,
    OpportunitySet,
)
from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.orchestration.workflow import build_workflow


class GoldenSpecialist:
    def __init__(self, name: str):
        self.name = name

    def analyze(self, context: AgentContext):
        from b3_agent.agents.specialists import SpecialistAnalysis
        return SpecialistAnalysis(
            agent=self.name,
            summary=f"Deterministic integration analysis for {self.name}.",
            findings=("Facts were received through the LangGraph context.",),
            risks=("Market conditions can change.",),
            evidence_refs=("golden:evidence",),
            source_refs=("golden:fixture",),
        )


class GoldenSynthesis:
    def synthesize(self, context: AgentContext):
        return {
            "summary": "Golden workflow synthesis.",
            "agreements": ["Deterministic context was preserved."],
            "conflicts": [],
            "uncertainties": ["Fixture is deterministic."],
            "evidence_gaps": [],
            "evidence_refs": ["golden:evidence"],
        }


class GoldenReasoning:
    def __init__(self, action: str = "HUMAN_REVIEW"):
        self.action = action

    def decide(self, context: AgentContext):
        from b3_agent.schemas.decision import DecisionProposal
        return DecisionProposal(
            action=self.action,
            subject_id="PORTFOLIO",
            thesis="Golden workflow proposal requires human review.",
            rationale="The proposal was produced after deterministic context, specialists and synthesis.",
            evidence_refs=("golden:evidence",),
            risks=("Fixture risk.",),
            opportunity_cost="Review alternatives.",
            capital_impact="No order executed.",
            confidence="TEST",
            invalidation_conditions=("Fixture changes.",),
            as_of=None,
        )


@dataclass
class GoldenKnowledgeContext:
    evidence: list[dict]
    graph_context: list[dict]
    sources: list[str]

    def as_dict(self):
        return {
            "evidence": self.evidence,
            "graph_context": self.graph_context,
            "sources": self.sources,
        }


class GoldenKnowledgeBuilder:
    def build(self, request, **kwargs):
        return GoldenKnowledgeContext(
            evidence=[{"evidence_id": "golden:evidence", "source_ref": "golden:fixture"}],
            graph_context=[],
            sources=["golden:fixture"],
        )


class GoldenRetriever:
    def retrieve(self, request, top_k=5):
        return ()


def _portfolio(cash: float = 80000.0) -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 18),
        cash=cash,
        positions=(
            Position(
                position_id="pos-PETR4",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=1000,
                average_cost=30.0,
                market_price=32.0,
                market_value=32000.0,
            ),
        ),
    )


def _opportunity_set(capital: float = 3000.0) -> OpportunitySet:
    opportunity = Opportunity(
        opportunity_id="SELL_PUT:PETRV300",
        ticker="PETR4",
        instrument_type="OPTION",
        action="SELL_PUT",
        as_of=date(2026, 9, 18),
        expected_return=0.12,
        capital_requirement=capital,
        evidence_refs=("golden:evidence",),
        source_refs=("golden:fixture",),
        rationale="Golden deterministic option opportunity.",
    )
    return OpportunitySet(
        as_of=date(2026, 9, 18),
        ranked_opportunities=(
            __import__("b3_agent.schemas.opportunity", fromlist=["OpportunityAssessment"]).OpportunityAssessment(
                opportunity_id=opportunity.opportunity_id,
                eligible=True,
                ticker=opportunity.ticker,
                instrument_type=opportunity.instrument_type,
                action=opportunity.action,
                as_of=opportunity.as_of,
                expected_return=opportunity.expected_return,
                capital_requirement=opportunity.capital_requirement,
                evidence_refs=opportunity.evidence_refs,
                source_refs=opportunity.source_refs,
                rationale=opportunity.rationale,
            ),
        ),
        rejected_opportunities=(),
        action_candidates=(
            ActionCandidate(
                action_candidate_id="ACTION:SELL_PUT:PETRV300",
                action_type="SELL_PUT",
                subject_id="SELL_PUT:PETRV300",
                as_of=date(2026, 9, 18),
                priority="NORMAL",
                opportunity_refs=("SELL_PUT:PETRV300",),
                evidence_refs=("golden:evidence",),
            ),
        ),
        quality_status="VALIDATED",
        ranking_policy_version="1.0",
        source_refs=("golden:fixture",),
    )


def _workflow():
    return build_workflow(
        retriever=GoldenRetriever(),
        knowledge_context_builder=GoldenKnowledgeBuilder(),
        memory_manager=None,
        market_agent=GoldenSpecialist("market_analysis"),
        portfolio_agent=GoldenSpecialist("portfolio_analysis"),
        options_agent=GoldenSpecialist("options_analysis"),
        synthesis_agent=GoldenSynthesis(),
        reasoning_agent=GoldenReasoning(),
        risk_validator=RiskValidator(),
    )


GOLDEN_CASES = {
    "C01": ("Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?", 80000.0, "PASS"),
    "C02": ("Tenho R$ 20 mil. Essa PUT cabe na minha carteira?", 20000.0, "PASS"),
    "C03": ("Existe alguma oportunidade que melhore minha diversificação?", 80000.0, "PASS"),
    "C04": ("Vale a pena analisar uma nova oportunidade em vez de manter essa posição?", 80000.0, "PASS"),
    "C05": ("É melhor comprar PETR4 ou vender uma PUT de PETR4?", 80000.0, "PASS"),
    "C06": ("PETR4 está barata?", 80000.0, "PASS"),
    "C07": ("Como está minha PUT e existe alguma alternativa que eu deveria analisar?", 80000.0, "PASS"),
    "C08": ("Qual a melhor coisa para eu fazer agora?", 80000.0, "PASS"),
}


@pytest.mark.parametrize("case_id", GOLDEN_CASES)
def test_golden_cases_execute_real_langgraph_workflow(case_id: str) -> None:
    request, cash, expected_status = GOLDEN_CASES[case_id]
    opportunity_set = _opportunity_set()
    workflow = _workflow()

    state = workflow.invoke({
        "user_question": request,
        "ticker": "PETR4",
        "as_of": date(2026, 9, 18),
        "portfolio_context": _portfolio(cash),
        "opportunity_set": opportunity_set,
    })

    assert state["status"] == expected_status
    assert state["deterministic_context"]["opportunity_set"]["ranked_opportunities"][0]["opportunity_id"] == "SELL_PUT:PETRV300"
    assert state["synthesis"]["summary"] == "Golden workflow synthesis."
    assert state["decision_proposal"]["subject_id"] == "PORTFOLIO"
    assert state["risk_validation"]["status"] == "PASS"
    assert state["audit"] == []
