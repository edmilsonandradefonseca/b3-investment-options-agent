"""HTTP application boundary for the V3.1 B3 orchestrator.

This layer is intentionally thin. It validates the transport payload, delegates
all workflow execution to ``b3_orchestrator`` and serializes its stable response.
No investment logic, provider access, ranking, reasoning, or risk bypass belongs
here.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from b3_agent.orchestration.orchestrator import b3_orchestrator


class OrchestratorHttpRequest(BaseModel):
    """Transport contract exposed by the V3.1 HTTP boundary."""

    task: str = Field(min_length=1)
    ticker: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class OrchestratorHttpResponse(BaseModel):
    """Stable JSON representation of ``OrchestratorResponse``."""

    status: str
    result: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    audit: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


app = FastAPI(
    title="B3 Investment & Options Agent",
    version="3.1",
    description="Thin HTTP boundary for the read-only B3 decision-support orchestrator.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return transport health without invoking the investment workflow."""
    return {"status": "ok"}


@app.post("/v1/orchestrate", response_model=OrchestratorHttpResponse)
def orchestrate(request: OrchestratorHttpRequest) -> OrchestratorHttpResponse:
    """Validate and delegate a request to the canonical B3 orchestrator."""
    response = b3_orchestrator(
        task=request.task,
        ticker=request.ticker,
        context=request.context,
    )
    return OrchestratorHttpResponse(
        status=response.status,
        result=response.result,
        sources=list(response.sources),
        audit=list(response.audit),
        error=response.error,
    )
