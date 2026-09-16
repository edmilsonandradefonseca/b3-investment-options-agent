from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from b3_agent.agents.context import AgentContext


@dataclass(frozen=True)
class SpecialistAnalysis:
    """Structured, non-decision analysis produced by a specialist agent."""

    agent: str
    summary: str
    findings: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    as_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "summary": self.summary,
            "findings": list(self.findings),
            "risks": list(self.risks),
            "evidence_refs": list(self.evidence_refs),
            "source_refs": list(self.source_refs),
            "as_of": self.as_of,
        }


@dataclass(frozen=True)
class SpecialistContext:
    """Immutable context supplied to a specialist; facts remain upstream-owned."""

    request: str
    deterministic_context: Mapping[str, Any] = field(default_factory=dict)
    retrieved_evidence: tuple[Mapping[str, Any], ...] = ()

    @classmethod
    def from_agent_context(cls, context: AgentContext) -> "SpecialistContext":
        return cls(
            request=context.request,
            deterministic_context=context.deterministic_context,
            retrieved_evidence=context.retrieved_evidence,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "deterministic_context": self.deterministic_context,
            "retrieved_evidence": list(self.retrieved_evidence),
        }
