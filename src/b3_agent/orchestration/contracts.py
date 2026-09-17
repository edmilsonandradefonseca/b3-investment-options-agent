from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, TypedDict

AS_OF = date | datetime

@dataclass(frozen=True)
class OrchestratorRequest:
    """Stable input boundary for the B3 investment intelligence workflow."""
    task: str
    ticker: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        task = self.task.strip()
        if not task:
            raise ValueError("task must not be empty")
        ticker = self.ticker.strip().upper() if self.ticker else None
        if ticker == "":
            ticker = None
        object.__setattr__(self, "task", task)
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "context", dict(self.context))
    @classmethod
    def from_inputs(cls, task: str, ticker: str | None = None, context: dict[str, Any] | None = None) -> "OrchestratorRequest":
        return cls(task=task, ticker=ticker, context=context or {})

class B3State(TypedDict, total=False):
    """Typed LangGraph state boundary defined by Architecture V3.1."""
    user_question: str
    ticker: str | None
    request: str
    deterministic_context: dict[str, Any]
    portfolio_context: Any
    opportunity_set: Any
    knowledge_context: dict[str, Any]
    memory_context: list[dict[str, Any]]
    rag_context: list[dict[str, Any]]
    graph_context: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    threats: list[dict[str, Any]]
    opportunities: list[dict[str, Any]]
    action_candidates: list[dict[str, Any]]
    fundamental_analysis: Any
    market_analysis: Any
    options_analysis: Any
    risk_analysis: Any
    market_agent_analysis: dict[str, Any]
    portfolio_agent_analysis: dict[str, Any]
    options_agent_analysis: dict[str, Any]
    synthesis: dict[str, Any]
    insights: list[dict[str, Any]]
    decision_proposal: dict[str, Any] | None
    proposal: dict[str, Any]
    risk_validation: dict[str, Any] | None
    status: str
    sources: list[str]
    audit: list[dict[str, Any]]

@dataclass(frozen=True)
class OrchestratorResponse:
    """Stable output boundary returned by the B3 investment workflow."""
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    sources: tuple[str, ...] = ()
    audit: tuple[dict[str, Any], ...] = ()
    error: str | None = None
    def __post_init__(self) -> None:
        status = self.status.strip().upper()
        if not status:
            raise ValueError("status must not be empty")
        if self.error is not None and not self.error.strip():
            raise ValueError("error must be non-empty when provided")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "result", dict(self.result))
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "audit", tuple(dict(item) for item in self.audit))
