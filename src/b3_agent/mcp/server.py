"""Model Context Protocol server for the B3 investment intelligence agent.

The MCP boundary is intentionally read-only: tools expose deterministic domain
capabilities to an AI client, while calculations and investment decisions remain
inside the B3 domain layer.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from b3_agent.config import settings
from b3_agent.portfolio import PortfolioIntelligenceEngine
from b3_agent.portfolio.ingestion import BtgRendaVariavelLoader
from b3_agent.portfolio.position_intelligence import PositionIntelligenceEngine
from b3_agent.repositories.portfolio import PortfolioRepository
from b3_agent.schemas.opportunity import OpportunitySet
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.valuation import ValuationRange


PortfolioLoader = Callable[[], PortfolioContext]
OpportunityLoader = Callable[[], OpportunitySet]
ValuationLoader = Callable[[str], ValuationRange | None]

_portfolio_loader: PortfolioLoader | None = None
_opportunity_loader: OpportunityLoader | None = None
_valuation_loader: ValuationLoader | None = None


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
    """Return the V3.1 deterministic MCP capability contract."""
    return {
        "server": "B3 Investment Intelligence",
        "version": "0.4.0",
        "mode": "read_only",
        "tools": [
            "get_portfolio_context",
            "get_portfolio_intelligence",
            "analyze_position",
            "get_valuation",
            "get_opportunities",
            "compare_position_opportunity",
        ],
        "governance": {
            "deterministic_first": True,
            "llm_executes_trades": False,
            "orders_supported": False,
        },
    }


@mcp.tool()
def get_portfolio_context() -> dict[str, Any]:
    """Return the current point-in-time portfolio snapshot from the configured source."""
    return _serialize(_load_portfolio_context())


@mcp.tool()
def get_portfolio_intelligence() -> dict[str, Any]:
    """Build deterministic portfolio intelligence from the current portfolio context."""
    context = _load_portfolio_context()
    intelligence = PortfolioIntelligenceEngine().build(context)
    return _serialize(intelligence)


@mcp.tool()
def analyze_position(position_id: str) -> dict[str, Any]:
    """Return deterministic lifecycle and exposure facts for one position."""
    normalized_id = position_id.strip()
    if not normalized_id:
        raise ValueError("position_id must not be empty")

    context = _load_portfolio_context()
    matches = tuple(
        position for position in context.positions if position.position_id == normalized_id
    )
    if not matches:
        raise ValueError(f"position_id not found: {normalized_id}")

    assessment = PositionIntelligenceEngine().assess(matches, as_of=context.as_of)
    return _serialize(assessment[0])


@mcp.tool()
def get_valuation(ticker: str) -> dict[str, Any]:
    """Return the configured deterministic valuation for one ticker.

    Valuation calculation belongs to the valuation domain. This MCP tool only
    exposes a previously produced ValuationRange through the transport boundary.
    """
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("ticker must not be empty")

    loader = _valuation_loader
    if loader is None:
        raise RuntimeError("valuation source is not configured")

    valuation = loader(normalized_ticker)
    if valuation is None:
        raise ValueError(f"valuation not found: {normalized_ticker}")
    return _serialize(valuation)


@mcp.tool()
def get_opportunities() -> dict[str, Any]:
    """Return the current deterministic OpportunitySet without re-ranking it."""
    opportunity_set = _load_opportunity_set()
    return _serialize(opportunity_set)


@mcp.tool()
def compare_position_opportunity(
    position_id: str,
    opportunity_id: str,
) -> dict[str, Any]:
    """Return an existing deterministic position/opportunity comparison, if present.

    The comparison is read from the OpportunitySet; this boundary does not invent
    portfolio-fit logic or recompute rankings.
    """
    position_key = position_id.strip()
    opportunity_key = opportunity_id.strip()
    if not position_key:
        raise ValueError("position_id must not be empty")
    if not opportunity_key:
        raise ValueError("opportunity_id must not be empty")

    context = _load_portfolio_context()
    if not any(position.position_id == position_key for position in context.positions):
        raise ValueError(f"position_id not found: {position_key}")

    opportunity_set = _load_opportunity_set()
    matches = tuple(
        item
        for item in opportunity_set.relative_opportunities
        if item.existing_position_id == position_key
        and item.candidate_opportunity_id == opportunity_key
    )
    if not matches:
        raise ValueError(
            "position/opportunity comparison not found: "
            f"{position_key} / {opportunity_key}"
        )
    return _serialize(matches[0])


def configure_mcp_sources(
    *,
    portfolio_loader: PortfolioLoader | None = None,
    opportunity_loader: OpportunityLoader | None = None,
    valuation_loader: ValuationLoader | None = None,
) -> None:
    """Inject deterministic domain sources at the MCP composition boundary."""
    global _portfolio_loader, _opportunity_loader, _valuation_loader
    _portfolio_loader = portfolio_loader
    _opportunity_loader = opportunity_loader
    _valuation_loader = valuation_loader


def _load_portfolio_context() -> PortfolioContext:
    if _portfolio_loader is not None:
        return _portfolio_loader()

    configured = os.getenv("B3_AGENT_PORTFOLIO_FILE")
    source_path = (
        Path(configured).expanduser().resolve()
        if configured
        else settings.data_dir / "portfolio.json"
    )

    if source_path.suffix.lower() in {".xlsx", ".xlsm"}:
        return BtgRendaVariavelLoader().load(source_path)

    return PortfolioRepository(source_path).load()


def _load_opportunity_set() -> OpportunitySet:
    if _opportunity_loader is None:
        raise RuntimeError("opportunity source is not configured")
    return _opportunity_loader()


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
