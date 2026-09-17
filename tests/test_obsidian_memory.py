from pathlib import Path

from b3_agent.knowledge.memory import InsightRecord, ObsidianMemoryManager
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore


def test_retrieve_context_returns_bounded_rag_and_memory_context(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "thesis.md").write_text(
        "# ITUB4\n\nInvestment thesis for ITUB4 and portfolio risk.",
        encoding="utf-8",
    )

    store = ObsidianKnowledgeStore(vault)
    manager = ObsidianMemoryManager(store)

    context = manager.retrieve_context("ITUB4 portfolio")

    assert context["memory_context"]
    assert context["rag_context"] == context["memory_context"]
    assert context["rag_context"][0]["relative_path"] == "thesis.md"


def test_persist_insight_creates_human_readable_note(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    manager = ObsidianMemoryManager(ObsidianKnowledgeStore(vault))
    path = manager.persist_insight(
        InsightRecord(
            insight_id="INS-20260916-001",
            entity="ITUB4",
            insight_type="risk",
            title="Portfolio concentration",
            statement="Concentration remains a material portfolio risk.",
            evidence=("obsidian:04_Stocks/ITUB4.md",),
            source="Risk Agent",
            confidence=0.91,
            status="active",
        )
    )

    assert path == Path(
        "00_System/Knowledge/Insights/INS-20260916-001/v1.md"
    )
    content = manager.store.read_note(path)
    assert "# Portfolio concentration" in content
    assert "- Insight ID: INS-20260916-001" in content
    assert "- Entity: ITUB4" in content
    assert "- Type: risk" in content
    assert "Concentration remains" in content


def test_persist_decision_is_separate_from_insight(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()

    manager = ObsidianMemoryManager(ObsidianKnowledgeStore(vault))
    path = manager.persist_decision(
        {
            "action": "HOLD",
            "subject_id": "ITUB4",
            "thesis": "Maintain current thesis.",
            "rationale": "Evidence remains supportive.",
            "evidence_refs": ["obsidian:04_Stocks/ITUB4.md"],
            "risks": ["Concentration"],
            "opportunity_cost": "None identified.",
            "capital_impact": "No change.",
            "confidence": 0.8,
            "invalidation_conditions": ["Thesis invalidated"],
        },
        request="Analyze ITUB4",
        ticker="ITUB4",
    )

    assert path.parent == Path("06_Decisions")
    content = manager.store.read_note(path)
    assert "Decision Proposal — ITUB4" in content
    assert "- Action: HOLD" in content
    assert "Analyze ITUB4" in content
