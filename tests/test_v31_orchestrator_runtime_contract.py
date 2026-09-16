from __future__ import annotations

from pathlib import Path

from b3_agent.config import settings
from b3_agent.orchestration.orchestrator import b3_orchestrator
from b3_agent.orchestration.runtime import configure_default_workflow


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

    monkeypatch.setattr(settings, "obsidian_vault", vault)
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_model", "test-model")

    import b3_agent.orchestration.runtime as runtime

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
