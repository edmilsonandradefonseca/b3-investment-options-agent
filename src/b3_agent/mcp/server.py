"""Model Context Protocol server for the B3 investment intelligence agent.

The MCP boundary is intentionally read-only: tools expose deterministic domain
capabilities to an AI client, while calculations and investment decisions remain
inside the B3 domain layer.
"""

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "B3 Investment Intelligence",
    instructions=(
        "Read-only interface to deterministic B3 portfolio, options, valuation "
        "and opportunity intelligence. Tool outputs are decision-support context, "
        "not executable trading orders."
    ),
)


@mcp.tool()
def get_system_capabilities() -> dict[str, object]:
    """Return the capabilities exposed by the B3 MCP server."""
    return {
        "server": "B3 Investment Intelligence",
        "version": "0.1.0",
        "mode": "read_only",
        "capabilities": [
            "portfolio_intelligence",
            "options_analysis",
            "valuation",
            "opportunity_intelligence",
            "market_context",
        ],
        "governance": {
            "deterministic_first": True,
            "llm_executes_trades": False,
            "orders_supported": False,
        },
    }


if __name__ == "__main__":
    mcp.run()
