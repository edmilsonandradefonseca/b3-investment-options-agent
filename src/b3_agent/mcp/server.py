"""Model Context Protocol server for the B3 investment intelligence agent.

The MCP boundary is intentionally read-only: tools expose deterministic domain
capabilities to an AI client, while calculations and investment decisions remain
inside the B3 domain layer.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from b3_agent.config import settings
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.repositories.portfolio import PortfolioRepository
from b3_agent.schemas.position import PortfolioContext


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
        "version": "0.2.0",
        "mode": "read_only",
        "capabilities": [
            "portfolio_context",
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


@mcp.tool()
def get_portfolio_context() -> dict[str, Any]:
    """Return the current point-in-time portfolio snapshot from the configured source.

    JSON sources use the normalized PortfolioRepository. XLSX sources use the
    existing deterministic BTG Renda Variavel ingestion pipeline. The tool never
    fabricates positions when the source is unavailable.
    """
    context = _load_portfolio_context()
    return _serialize(context)


@mcp.tool()
def get_portfolio_intelligence() -> dict[str, Any]:
    """Build deterministic portfolio intelligence from the current portfolio context."""
    context = _load_portfolio_context()
    intelligence = PortfolioIntelligenceEngine().build(context)
    return _serialize(intelligence)


def _load_portfolio_context() -> PortfolioContext:
    configured = os.getenv("B3_AGENT_PORTFOLIO_FILE")
    source_path = (
        Path(configured).expanduser().resolve()
        if configured
        else settings.data_dir / "portfolio.json"
    )

    if source_path.suffix.lower() in {".xlsx", ".xlsm"}:
        return BtgRendaVariavelLoader().load(source_path)

    return PortfolioRepository(source_path).load()


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return _serialize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    mcp.run()
