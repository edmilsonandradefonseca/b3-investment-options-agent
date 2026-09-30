from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Iterable

from b3_agent.knowledge.evidence import Evidence


class ContinuousTriageAction(StrEnum):
    SKIP = "SKIP"
    RELEVANCE_SCREEN = "RELEVANCE_SCREEN"
    DOSSIER = "DOSSIER"


@dataclass(frozen=True, slots=True)
class ContinuousTriageDecision:
    action: ContinuousTriageAction
    reason: str
    tickers: tuple[str, ...]
    evidence_fingerprint: str


def triage_official_evidence(
    evidence: Evidence,
    *,
    monitored_tickers: Iterable[str],
    as_of: datetime,
    max_age: timedelta = timedelta(days=7),
) -> ContinuousTriageDecision:
    metadata = evidence.metadata
    monitored = {
        str(ticker).upper().strip()
        for ticker in monitored_tickers
        if str(ticker).strip()
    }
    mapped = tuple(
        ticker for ticker in metadata.ticker_refs if ticker in monitored
    )
    fingerprint = canonical_evidence_fingerprint(evidence)

    if metadata.source_class != "OFFICIAL_REGULATORY" or metadata.authority_tier != 0:
        return ContinuousTriageDecision(
            ContinuousTriageAction.SKIP,
            "SOURCE_NOT_OFFICIAL_TIER0",
            mapped,
            fingerprint,
        )

    if not metadata.ticker_refs:
        return ContinuousTriageDecision(
            ContinuousTriageAction.SKIP,
            "UNMAPPED_ISSUER",
            (),
            fingerprint,
        )

    if not mapped:
        return ContinuousTriageDecision(
            ContinuousTriageAction.SKIP,
            "OUTSIDE_MONITORED_UNIVERSE",
            (),
            fingerprint,
        )

    observed = (
        metadata.observed_at
        or metadata.retrieved_at
        or metadata.reference_at
        or metadata.published_at
    )
    if observed is not None and as_of - observed > max_age:
        return ContinuousTriageDecision(
            ContinuousTriageAction.SKIP,
            "STALE_EVIDENCE",
            mapped,
            fingerprint,
        )

    if metadata.materiality == "MATERIAL":
        return ContinuousTriageDecision(
            ContinuousTriageAction.DOSSIER,
            "OFFICIAL_MATERIAL",
            mapped,
            fingerprint,
        )

    if metadata.materiality == "CANDIDATE":
        return ContinuousTriageDecision(
            ContinuousTriageAction.RELEVANCE_SCREEN,
            "OFFICIAL_CANDIDATE",
            mapped,
            fingerprint,
        )

    return ContinuousTriageDecision(
        ContinuousTriageAction.SKIP,
        "NON_MATERIAL",
        mapped,
        fingerprint,
    )


def canonical_evidence_fingerprint(evidence: Evidence) -> str:
    metadata = evidence.metadata
    stable = "|".join(
        [
            metadata.source or "",
            evidence.source_url or "",
            metadata.cvm_code or "",
            metadata.reference_at.isoformat() if metadata.reference_at else "",
            evidence.title,
            evidence.content_hash or "",
        ]
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
