import pytest

from b3_agent.orchestration.contracts import OrchestratorRequest
from b3_agent.routing.lab_clarification import lab_operation_clarification


@pytest.mark.parametrize("question", [
    "Vale manter, encerrar ou rolar uma opção da minha carteira?",
    "Quero vender PUT de PETR4.",
    "Quero encerrar minha CALL de PETR4.",
])
def test_operation_requires_exact_contract(question):
    result = lab_operation_clarification(OrchestratorRequest(question, context={"workspace": "Strategy Lab"}))
    assert result["lab_clarification"]["missing_fields"] == ["option_id"]
    assert result["lab_clarification"]["original_question"] == question
    assert result["telemetry"] == {"llm_calls": 0, "option_chain_calls": 0}


@pytest.mark.parametrize("question,context", [
    ("Explique a rolagem de opções.", {"workspace": "Strategy Lab"}),
    ("Quais evidências sustentam minha tese de queda de PETR4?", {"workspace": "Strategy Lab"}),
    ("Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?", {"workspace": "Strategy Lab"}),
    ("Quero encerrar a CALL PETRK376.", {"workspace": "Strategy Lab"}),
    ("Quero vender PUT de PETR4.", {"workspace": "Strategy Lab", "comparison_assets": ["PETR4", "PETR4"], "option_a": "PETRV300"}),
    ("Quero vender PUT de PETR4.", {"workspace": "Opportunities"}),
])
def test_clarification_does_not_override_other_intents(question, context):
    assert lab_operation_clarification(OrchestratorRequest(question, context=context)) is None


def test_http_clarification_precedes_all_provider_and_senior_dispatch(monkeypatch):
    from fastapi.testclient import TestClient
    from b3_agent import server
    def unexpected(*args, **kwargs):
        raise AssertionError("Clarification must not start any acquisition or senior call")
    for name in ("_configure_runtime", "_dispatch_fast_route", "_dispatch_opportunity_screen", "_workspace_intelligence_response"):
        monkeypatch.setattr(server, name, unexpected)
    response = TestClient(server.app).post("/orchestrate", json={"task": "Vale manter, encerrar ou rolar uma opção da minha carteira?", "context": {"workspace": "Strategy Lab"}})
    assert response.status_code == 200
    assert response.json()["status"] == "NEEDS_CLARIFICATION"
    assert response.json()["result"]["derived_synthesis_status"] == "NOT_REQUESTED"
