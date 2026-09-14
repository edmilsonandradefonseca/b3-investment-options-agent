from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .call import CallOpportunity
from .put import PutOpportunity


@dataclass(frozen=True)
class OptionsAnalysis:
    """Unified deterministic result for PUT and covered CALL analysis."""

    puts: tuple[PutOpportunity, ...] = ()
    calls: tuple[CallOpportunity, ...] = ()
    source_refs: tuple[str, ...] = ()
    quality_status: str = "VALIDATED"
    assumptions: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.quality_status not in {"VALIDATED", "WARNING", "REJECTED"}:
            raise ValueError("invalid quality_status")

    @property
    def opportunities(self) -> tuple[PutOpportunity | CallOpportunity, ...]:
        return self.puts + self.calls


class OptionsAnalysisEngine:
    """Combines already validated deterministic PUT/CALL results without refetching data."""

    def combine(
        self,
        *,
        puts: tuple[PutOpportunity, ...] = (),
        calls: tuple[CallOpportunity, ...] = (),
        source_refs: tuple[str, ...] = (),
        quality_status: str = "VALIDATED",
        assumptions: dict[str, Any] | None = None,
    ) -> OptionsAnalysis:
        return OptionsAnalysis(
            puts=puts,
            calls=calls,
            source_refs=source_refs,
            quality_status=quality_status,
            assumptions=assumptions,
        )
