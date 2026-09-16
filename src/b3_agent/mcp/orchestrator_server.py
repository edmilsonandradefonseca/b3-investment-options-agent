"""MCP transport adapter for the V3.1 B3 orchestrator.

The transport layer is intentionally thin: request validation and workflow
execution remain behind ``b3_orchestrator``. This module exposes the logical
orchestrator as a read-only decision-support operation and never places orders.
"""

from __future__ import annotations

from typing import Any

from b3_agent.orchestration.orchestrator import b3_orchestrator


def analyze_b3(
    task: str,
    ticker: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the V3.1 B3 orchestrator and serialize its stable response boundary."""
    response = b3_orchestrator(task=task, ticker=ticker, context=context)
    return {
        "status": response.status,
        "result": response.result,
        "sources": list(response.sources),
        "audit": list(response.audit),
        "error": response.error,
    }
