from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from b3_agent.config import settings
from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.orchestration.orchestrator import b3_orchestrator
from b3_agent.orchestration.runtime import configure_default_workflow
from b3_agent.schemas.opportunity import Opportunity


def test_default_runtime_composes_orchestrator_with_langgraph(monkeypatch, tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "PETR4.md").write_text(
        "# PETR4\n\nDeterministic runtime contract evidence.",
        encoding="utf-8",
    )

    class FakeLLM:
        def complete_json(self, *, instructions, input_text, schema_name, schema):
            return {
                "action": "NO_CHANGE",
                "subject_id": "PETR4",
                "thesis": "Keep the current thesis.",
                "rationale": "Runtime composition contract.",
                "evidence_refs": ["obsidian:PETR4.md"],
                "risks": [],
                "opportunity_cost": "None identified.",
                "capital_impact": "None.",
                "confidence": "MEDIUM",
                "invalidation_conditions": [],
            }

    monkeypatch.setattr(
        "b3_agent.config.settings",
        replace(
            settings,
            obsidian_vault=vault,
            llm_enabled=True,
            llm_model="test-model",
        ),
    )

    import b3_agent.orchestration.runtime as runtime

    monkeypatch.setattr(runtime, "settings", __import__("b3_agent.config", fromlist=["settings"]).settings)
    monkeypatch.setattr(runtime, "OpenAIResponsesClient", lambda model: FakeLLM())
    configure_default_workflow(vault_path=vault)

    response = b3_orchestrator(
        "Analyze PETR4 thesis",
        "petr4",
        {"sources": ["runtime-contract"]},
    )

    assert response.status == "PASS"
    assert response.result["ticker"] == "PETR4"
    assert response.result["decision_proposal"]["action"] == "NO_CHANGE"
    assert response.result["risk_validation"]["status"] == "PASS"


def test_default_runtime_injects_deterministic_context(monkeypatch, tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "PETR4.md").write_text(
        "# PETR4\n\nDeterministic context injection evidence.",
        encoding="utf-8",
    )

    class FakeLLM:
        def complete_json(self, *, instructions, input_text, schema_name, schema):
            return {
                "action": "NO_CHANGE",
                "subject_id": "PETR4",
                "thesis": "Context injection contract.",
                "rationale": "Deterministic context reached reasoning.",
                "evidence_refs": ["obsidian:PETR4.md"],
                "risks": [],
                "opportunity_cost": "None.",
                "capital_impact": "None.",
                "confidence": "MEDIUM",
                "invalidation_conditions": [],
            }

    monkeypatch.setattr(
        "b3_agent.config.settings",
        replace(settings, obsidian_vault=vault, llm_enabled=True, llm_model="test-model"),
    )
    import b3_agent.orchestration.runtime as runtime
    monkeypatch.setattr(runtime, "settings", __import__("b3_agent.config", fromlist=["settings"]).settings)
    monkeypatch.setattr(runtime, "OpenAIResponsesClient", lambda model: FakeLLM())

    as_of = date(2026, 9, 15)
    opportunity = Opportunity(
        opportunity_id="OPP:PETR4:1",
        ticker="PETR4",
        instrument_type="STOCK",
        action="BUY",
        as_of=as_of,
        expected_return=0.12,
        capital_requirement=1000.0,
        evidence_refs=("evidence:PETR4",),
        source_refs=("brapi",),
        quality_status="VALIDATED",
        rationale="Runtime fixture.",
    )
    opportunity_set = OpportunityPipeline().build((opportunity,), as_of=as_of)
    portfolio_context = {"as_of": as_of.isoformat(), "position_ids": ["btg:PETR4"]}

    configure_default_workflow(
        vault_path=vault,
        portfolio_context=portfolio_context,
        opportunity_set=opportunity_set,
    )

    response = b3_orchestrator("Analyze PETR4", "petr4")

    assert response.status == "PASS"
    assert response.result["portfolio_context"] == portfolio_context
    assert response.result["opportunities"][0]["opportunity_id"] == "OPP:PETR4:1"
