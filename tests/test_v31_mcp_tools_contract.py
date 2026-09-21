from __future__ import annotations

from datetime import date

import pytest

from b3_agent.mcp import server
from b3_agent.schemas.opportunity import (
    OpportunityAssessment,
    OpportunitySet,
    RelativeOpportunity,
)
from b3_agent.schemas.position import PortfolioContext, Position
from b3_agent.schemas.valuation import ValuationRange


@pytest.fixture(autouse=True)
def reset_mcp_sources():
    server.configure_mcp_sources()
    yield
    server.configure_mcp_sources()


def _portfolio() -> PortfolioContext:
    return PortfolioContext(
        as_of=date(2026, 9, 15),
        positions=(
            Position(
                position_id="btg:PETR4",
                ticker="PETR4",
                instrument_type="STOCK",
                quantity=100,
                average_cost=30.0,
                market_price=35.0,
                market_value=3500.0,
            ),
        ),
        cash=1000.0,
        source_refs=("BTG:Renda Variavel",),
    )


def _opportunities() -> OpportunitySet:
    return OpportunitySet(
        as_of=date(2026, 9, 15),
        ranked_opportunities=(
            OpportunityAssessment(
                opportunity_id="opp:petr4:1",
                eligible=True,
                ticker="PETR4",
                instrument_type="STOCK",
                action="BUY",
                as_of=date(2026, 9, 15),
                expected_return=0.15,
                source_refs=("BRAPI",),
            ),
        ),
        rejected_opportunities=(),
        relative_opportunities=(
            RelativeOpportunity(
                relative_opportunity_id="rel:1",
                existing_position_id="btg:PETR4",
                existing_ticker="PETR4",
                candidate_opportunity_id="opp:petr4:1",
                candidate_ticker="PETR4",
                as_of=date(2026, 9, 15),
                comparison_refs=("comparison:deterministic",),
                relative_assessment="existing-position comparison available",
            ),
        ),
        ranking_policy_version="v3.1",
        source_refs=("OpportunityPipeline",),
    )


def _valuation() -> ValuationRange:
    return ValuationRange(
        instrument_id="PETR4",
        ticker="PETR4",
        as_of=date(2026, 9, 15),
        method="PE",
        bear_value=25.0,
        base_value=35.0,
        bull_value=45.0,
        accumulation_price=31.5,
        reduce_price=35.0,
        sell_price=45.0,
        source_refs=("valuation-engine",),
    )


def test_capability_contract_exposes_v31_tools_and_memory_write():
    result = server.get_system_capabilities()

    assert result["version"] == "0.5.0"
    assert result["tools"] == [
        "get_portfolio_context",
        "get_portfolio_intelligence",
        "analyze_position",
        "get_valuation",
        "get_opportunities",
        "compare_position_opportunity",
        "persist_insight",
        "persist_decision",
        "search_memory",
        "read_memory",
    ]
    assert result["governance"]["orders_supported"] is False


def test_search_memory_reads_existing_obsidian_notes(tmp_path):
    from b3_agent.knowledge.memory import ObsidianMemoryManager
    from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore

    vault = tmp_path / "vault"
    vault.mkdir()
    store = ObsidianKnowledgeStore(vault)
    store.write_note(
        "00_System/PROJECT_STATE.md",
        "# Project State

MCP bridge is active.",
    )
    server.configure_mcp_sources(memory_manager=ObsidianMemoryManager(store))

    result = server.search_memory("MCP bridge")

    assert result["query"] == "MCP bridge"
    assert result["matches"] == ["00_System/PROJECT_STATE.md"]


def test_read_memory_returns_existing_obsidian_note(tmp_path):
    from b3_agent.knowledge.memory import ObsidianMemoryManager
    from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore

    vault = tmp_path / "vault"
    vault.mkdir()
    store = ObsidianKnowledgeStore(vault)
    store.write_note(
        "00_System/PROJECT_STATE.md",
        "# Project State

MCP bridge is active.",
    )
    server.configure_mcp_sources(memory_manager=ObsidianMemoryManager(store))

    result = server.read_memory("00_System/PROJECT_STATE.md")

    assert result["path"] == "00_System/PROJECT_STATE.md"
    assert "MCP bridge is active." in result["content"]


def test_memory_tools_reject_empty_arguments():
    with pytest.raises(ValueError, match="query must not be empty"):
        server.search_memory("   ")
    with pytest.raises(ValueError, match="path must not be empty"):
        server.read_memory("   ")


def test_portfolio_context_and_intelligence_use_injected_domain_source():
    server.configure_mcp_sources(portfolio_loader=_portfolio)

    context = server.get_portfolio_context()
    intelligence = server.get_portfolio_intelligence()

    assert context["as_of"] == "2026-09-15"
    assert context["positions"][0]["position_id"] == "btg:PETR4"
    assert intelligence["as_of"] == "2026-09-15"


def test_analyze_position_delegates_to_existing_deterministic_engine():
    server.configure_mcp_sources(portfolio_loader=_portfolio)

    result = server.analyze_position("btg:PETR4")

    assert result["position_id"] == "btg:PETR4"
    assert result["ticker"] == "PETR4"
    assert result["side"] == "LONG"
    assert result["assignment_capital"] == 0.0


def test_valuation_exposes_precomputed_deterministic_range():
    server.configure_mcp_sources(
        valuation_loader=lambda ticker: _valuation() if ticker == "PETR4" else None
    )

    result = server.get_valuation("petr4")

    assert result["ticker"] == "PETR4"
    assert result["method"] == "PE"
    assert result["base_value"] == 35.0
    assert result["source_refs"] == ["valuation-engine"]


def test_opportunities_exposes_existing_opportunity_set_without_recomputation():
    server.configure_mcp_sources(opportunity_loader=_opportunities)

    result = server.get_opportunities()

    assert result["as_of"] == "2026-09-15"
    assert result["ranking_policy_version"] == "v3.1"
    assert result["ranked_opportunities"][0]["opportunity_id"] == "opp:petr4:1"


def test_compare_position_opportunity_exposes_existing_relative_assessment():
    server.configure_mcp_sources(
        portfolio_loader=_portfolio,
        opportunity_loader=_opportunities,
    )

    result = server.compare_position_opportunity("btg:PETR4", "opp:petr4:1")

    assert result["relative_opportunity_id"] == "rel:1"
    assert result["existing_position_id"] == "btg:PETR4"
    assert result["candidate_opportunity_id"] == "opp:petr4:1"


def test_mcp_tools_reject_unknown_or_unconfigured_resources():
    server.configure_mcp_sources(portfolio_loader=_portfolio)

    with pytest.raises(ValueError, match="position_id not found"):
        server.analyze_position("missing")

    with pytest.raises(RuntimeError, match="valuation source is not configured"):
        server.get_valuation("PETR4")

    with pytest.raises(RuntimeError, match="opportunity source is not configured"):
        server.get_opportunities()
