from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class AgentContext:
    """Immutable boundary presented to an investment reasoning agent.

    Deterministic facts are produced upstream. Agents may interpret these facts,
    but must not replace, rank, recalculate, or mutate them.
    """

    request: str
    deterministic_context: Mapping[str, Any] = field(default_factory=dict)
    retrieved_evidence: tuple[Mapping[str, Any], ...] = ()

    def to_payload(self) -> dict[str, Any]:
        """Return the stable payload used at the LLM boundary."""
        return {
            "request": self.request,
            "deterministic_context": self.deterministic_context,
            "retrieved_evidence": list(self.retrieved_evidence),
        }
