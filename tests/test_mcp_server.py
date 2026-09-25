import json
from datetime import date

from b3_agent.knowledge.memory import ObsidianMemoryManager
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.mcp.server import (
    configure_mcp_sources,
    get_portfolio_context,
    get_portfolio_intelligence,
    get_system_capabilities,
    persist_decision,
    persist_insight,
)


def test_mcp_capabilities_expose_controlled_memory_write():
    capabilities = get_system_capabilities()

    assert capabilities["mode"] == "controlled_write"
    assert "persist_insight" in capabilities["tools"]
    assert "persist_decision" in capabilities["tools"]
    assert "memory_write" in capabilities["capabilities"]
    assert capabilities["governance"]["deterministic_first"] is True
    assert capabilities["governance"]["llm_executes_trades"] is False
    assert capabilities["governance"]["orders_supported"] is False
    assert "get_portfolio_context" in capabilities["capabilities"]
    assert "get_portfolio_intelligence" in capabilities["capabilities"]


def test_get_portfolio_context_uses_configured_source(tmp_path, monkeypatch):
    source = tmp_path / "portfolio.json"
    source.write_text(
        json.dumps(
            {
                "as_of": "2026-09-15",
                "cash": 10000,
                "source_refs": ["test:portfolio"],
                "quality_status": "VALIDATED",
                "positions": [
                    {
                        "position_id": "POS-ITUB4",
                        "ticker": "ITUB4",
                        "instrument_type": "STOCK",
                        "quantity": 100,
                        "average_cost": 30.0,
                        "market_price": 35.0,
                        "market_value": 3500.0,
                        "source_ref": "test:portfolio",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("B3_AGENT_PORTFOLIO_FILE", str(source))

    result = get_portfolio_context()

    assert result["as_of"] == date(2026, 9, 15).isoformat()
    assert result["cash"] == 10000.0
    assert result["quality_status"] == "VALIDATED"
    assert result["positions"][0]["ticker"] == "ITUB4"
    assert result["positions"][0]["market_value"] == 3500.0


def test_get_portfolio_intelligence_builds_from_real_context(tmp_path, monkeypatch):
    source = tmp_path / "portfolio.json"
    source.write_text(
        json.dumps(
            {
                "as_of": "2026-09-15",
                "cash": 10000,
                "source_refs": ["test:portfolio"],
                "quality_status": "VALIDATED",
                "positions": [
                    {
                        "position_id": "POS-ITUB4",
                        "ticker": "ITUB4",
                        "instrument_type": "STOCK",
                        "quantity": 100,
                        "average_cost": 30.0,
                        "market_price": 35.0,
                        "market_value": 3500.0,
                        "source_ref": "test:portfolio",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("B3_AGENT_PORTFOLIO_FILE", str(source))

    result = get_portfolio_intelligence()

    assert result["as_of"] == "2026-09-15"
    assert len(result["assessments"]) == 1
    assert len(result["exposures"]) == 1
    assert result["exposures"][0]["ticker"] == "ITUB4"


def test_persist_insight_writes_through_memory_manager(tmp_path):
    vault = tmp_path / "vault"
    manager = ObsidianMemoryManager(ObsidianKnowledgeStore(vault))
    configure_mcp_sources(memory_manager=manager)

    result = persist_insight({
        "insight_id": "INS-TEST-001",
        "entity": "ITUB4",
        "insight_type": "assessment",
        "title": "Test insight",
        "statement": "Test statement",
        "evidence": ["test:evidence"],
        "source": "test",
        "confidence": 0.8,
    })

    assert result["status"] == "persisted"
    assert result["type"] == "insight"
    assert result["path"] == "00_System/Knowledge/Insights/INS-TEST-001/v1.md"
    assert (vault / result["path"]).is_file()


def test_persist_decision_writes_proposal_without_order_capability(tmp_path):
    vault = tmp_path / "vault"
    manager = ObsidianMemoryManager(ObsidianKnowledgeStore(vault))
    configure_mcp_sources(memory_manager=manager)

    result = persist_decision(
        {"id": "DEC-TEST-001", "subject_id": "ITUB4", "action": "HOLD"},
        request="Test decision request",
        ticker="ITUB4",
    )

    assert result["status"] == "persisted"
    assert result["type"] == "decision"
    assert result["path"] == "06_Decisions/DEC-TEST-001.md"
    assert (vault / result["path"]).is_file()
