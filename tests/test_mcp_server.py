import json
from datetime import date

from b3_agent.mcp.server import get_portfolio_context, get_portfolio_intelligence, get_system_capabilities


def test_mcp_capabilities_are_read_only():
    capabilities = get_system_capabilities()

    assert capabilities["mode"] == "read_only"
    assert capabilities["governance"]["deterministic_first"] is True
    assert capabilities["governance"]["llm_executes_trades"] is False
    assert capabilities["governance"]["orders_supported"] is False
    assert "portfolio_context" in capabilities["capabilities"]
    assert "portfolio_intelligence" in capabilities["capabilities"]


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
