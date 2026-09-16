from datetime import date

from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.orchestration.deterministic import opportunity_set_state
from b3_agent.orchestration.orchestrator import b3_orchestrator, configure_workflow
from b3_agent.orchestration.workflow import build_workflow
from b3_agent.schemas.opportunity import Opportunity


AS_OF = date(2026, 9, 15)


class _Retriever:
    def retrieve(self, query: str, *, top_k: int = 5):
        return ()


class _RiskValidator:
    def validate(self, decision):
        return type("RiskResult", (), {"status": "PASS", "reasons": ()})()


class _ReasoningAgent:
    def __init__(self):
        self.context = None

    def decide(self, context):
        self.context = context
        return type(
            "Decision",
            (),
            {
                "action": "NO_CHANGE",
                "subject_id": "PETR4",
                "thesis": "Deterministic context boundary.",
                "rationale": "Contract test.",
                "evidence_refs": (),
                "risks": (),
                "opportunity_cost": "None.",
                "capital_impact": "None.",
                "confidence": "MEDIUM",
                "invalidation_conditions": (),
                "as_of": None,
            },
        )()


def _opportunity_set():
    opportunity = Opportunity(
        opportunity_id="OPP:PETR4:1",
        ticker="PETR4",
        instrument_type="STOCK",
        action="BUY",
        as_of=AS_OF,
        expected_return=0.12,
        capital_requirement=1000.0,
        evidence_refs=("evidence:PETR4",),
        source_refs=("brapi",),
        quality_status="VALIDATED",
        rationale="Deterministic fixture.",
    )
    return OpportunityPipeline().build((opportunity,), as_of=AS_OF)


def test_orchestrator_passes_deterministic_portfolio_and_opportunity_context_to_reasoning():
    reasoning = _ReasoningAgent()
    configure_workflow(
        build_workflow(
            retriever=_Retriever(),
            reasoning_agent=reasoning,
            risk_validator=_RiskValidator(),
        )
    )

    portfolio_context = {"as_of": AS_OF.isoformat(), "position_ids": ["btg:PETR4"]}
    opportunity_set = _opportunity_set()

    response = b3_orchestrator(
        "Analyze PETR4",
        "petr4",
        {
            "portfolio_context": portfolio_context,
            **opportunity_set_state(opportunity_set),
        },
    )

    assert response.status == "PASS"
    assert reasoning.context.deterministic_context["portfolio_context"] == portfolio_context
    assert reasoning.context.deterministic_context["opportunity_set"]["ranked_opportunities"][0]["opportunity_id"] == "OPP:PETR4:1"
    assert reasoning.context.deterministic_context["action_candidates"][0]["opportunity_refs"] == ["OPP:PETR4:1"]
