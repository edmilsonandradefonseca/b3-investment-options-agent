from b3_agent.mcp.server import get_system_capabilities


def test_mcp_capabilities_are_read_only():
    capabilities = get_system_capabilities()

    assert capabilities["mode"] == "read_only"
    assert capabilities["governance"]["deterministic_first"] is True
    assert capabilities["governance"]["llm_executes_trades"] is False
    assert capabilities["governance"]["orders_supported"] is False
    assert "portfolio_intelligence" in capabilities["capabilities"]
    assert "opportunity_intelligence" in capabilities["capabilities"]
