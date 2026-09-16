from __future__ import annotations

from b3_agent.mcp.server import mcp


def test_mcp_exposes_v31_orchestrator_operation() -> None:
    tools = mcp._tool_manager.list_tools()
    names = {tool.name for tool in tools}
    assert "analyze_portfolio" in names


def test_mcp_capabilities_declare_orchestrated_analysis() -> None:
    from b3_agent.mcp.server import get_system_capabilities

    capabilities = get_system_capabilities()
    assert capabilities["mode"] == "read_only"
    assert "orchestrated_analysis" in capabilities["capabilities"]
    assert capabilities["governance"]["orders_supported"] is False
