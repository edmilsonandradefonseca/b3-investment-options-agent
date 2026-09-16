from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

from b3_agent.config import settings
from b3_agent.opportunity_pipeline import OpportunityPipeline
from b3_agent.orchestration.orchestrator import b3_orchestrator
from b3_agent.orchestration.runtime import configure_default_workflow
from b3_agent.schemas.opportunity import Opportunity


def _fake_llm():
    class FakeLLM:
        def complete_json(self, *, instructions, input_text, schema_name, schema):
            if schema_name.endswith("_analysis"):
                return {
                    "summary": "Specialist test analysis.",
                    "findings": ["Facts supplied upstream."],
                    "risks": ["Conditions may change."],
                    "evidence_refs": ["obsidian:PETR4.md"],
                    "source_refs": ["test:runtime"],
                }
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
    return FakeLLM()


def _configure(monkeypatch, vault):
    monkeypatch.setattr(
        "b3_agent.config.settings",
        replace(settings, obsidian_vault=vault, llm_enabled=True, llm_model="test-model"),
    )
    import b3_agent.orchestration.runtime as runtime
    monkeypatch.setattr(runtime, "settings", __import__("b3_agent.config", fromlist=["settings"]).settings)
    monkeypatch.setattr(runtime, "OpenAIResponsesClient", lambda model: _fake_llm())


def test_default_runtime_composes_orchestrator_with_langgraph(monkeypatch, tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "PETR4.md").write_text("# PETR4\n\nDeterministic runtime contract evidence.", encoding="utf-8")
    _configure(monkeypatch, vault)
    configure_default_workflow(vault_path=vault)

    response = b3_orchestrator("Analyze PETR4 thesis", "petr4", {"sources": ["runtime-contract"]})

    assert response.status == "PASS"
    assert response.result["ticker"] == "PETR4"
    assert response.result["decision_proposal"]["action"] == "NO_CHANGE"
    assert response.result["risk_validation"]["status"] == "PASS"
    assert response.result["market_agent_analysis"]["agent"] == "market_analysis"
    assert response.result["portfolio_agent_analysis"]["agent"] == "portfolio_analysis"
    assert response.result["options_agent_analysis"]["agent"] == "options_analysis"


def test_default_runtime_injects_deterministic_context(monkeypatch, tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "PETR4.md").write_text("# PETR4\n\nDeterministic context injection evidence.", encoding="utf-8")
    _configure(monkeypatch, vault)

    as_of = date(2026, 9, 15)
    opportunity = Opportunity(
        opportunity_id="OPP:PETR4:1", ticker="PETR4", instrument_type="STOCK", action="BUY",
        as_of=as_of, expected_return=0.12, capital_requirement=1000.0,
        evidence_refs=("evidence:PETR4",), source_refs=("brapi",),
        quality_status="VALIDATED", rationale="Runtime fixture.",
    )
    opportunity_set = OpportunityPipeline().build((opportunity,), as_of=as_of)
    portfolio_context = {"as_of": as_of.isoformat(), "position_ids": ["btg:PETR4"]}
    configure_default_workflow(vault_path=vault, portfolio_context=portfolio_context, opportunity_set=opportunity_set)

    response = b3_orchestrator("Analyze PETR4", "petr4")

    assert response.status == "PASS"
    assert response.result["portfolio_context"] == portfolio_context
    assert response.result["opportunities"][0]["opportunity_id"] == "OPP:PETR4:1"
    assert response.result["market_agent_analysis"]["agent"] == "market_analysis"
