from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from b3_agent.intelligence.local_evidence_analysis import (
    LocalEvidenceContextSelector,
)


@dataclass(frozen=True, slots=True)
class SeniorEvidenceContext:
    ticker: str
    canonical_evidence: tuple[dict[str, Any], ...]
    local_dossier_status: str
    local_dossier_reasons: tuple[str, ...]
    local_dossier: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "canonical_evidence": list(self.canonical_evidence),
            "local_dossier_status": self.local_dossier_status,
            "local_dossier_reasons": list(self.local_dossier_reasons),
            "local_dossier": self.local_dossier,
        }


class SeniorEvidenceContextBuilder:
    """Build senior context without waiting for local reasoning."""

    def __init__(self, selector: LocalEvidenceContextSelector):
        self.selector = selector

    def build(
        self,
        *,
        ticker: str,
        evidence_events: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        as_of: datetime | None = None,
    ) -> SeniorEvidenceContext:
        canonical = tuple(dict(item) for item in evidence_events)
        selected = self.selector.select(
            ticker=ticker,
            evidence_events=canonical,
            as_of=as_of,
        )
        dossier_payload = (
            selected.dossier.as_dict()
            if selected.dossier is not None
            else None
        )
        return SeniorEvidenceContext(
            ticker=ticker.upper().strip(),
            canonical_evidence=canonical,
            local_dossier_status=selected.status,
            local_dossier_reasons=selected.reasons,
            local_dossier=dossier_payload,
        )
