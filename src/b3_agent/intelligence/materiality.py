from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class Materiality(StrEnum):
    MATERIAL = "MATERIAL"
    CANDIDATE = "CANDIDATE"
    NON_MATERIAL = "NON_MATERIAL"


@dataclass(frozen=True)
class MaterialityDecision:
    materiality: Materiality
    reason: str
    policy_version: str = "v4.2-official-1"


def classify_official_disclosure(
    *,
    category: str | None,
    disclosure_type: str | None = None,
    species: str | None = None,
) -> MaterialityDecision:
    """Deterministic, source-aware materiality for official disclosures.

    Official documents must not be forced through the generic web-news
    keyword heuristic. Fato Relevante is material by source/category rule.
    Other common IPE categories start as candidates until dedicated rules
    are added and validated.
    """

    normalized = " | ".join(
        _normalize(value)
        for value in (category, disclosure_type, species)
        if value
    )

    if "fato relevante" in normalized:
        return MaterialityDecision(
            materiality=Materiality.MATERIAL,
            reason="OFFICIAL_FATO_RELEVANTE",
        )
    if "comunicado ao mercado" in normalized:
        return MaterialityDecision(
            materiality=Materiality.CANDIDATE,
            reason="OFFICIAL_COMUNICADO_AO_MERCADO",
        )
    if "aviso aos acionistas" in normalized:
        return MaterialityDecision(
            materiality=Materiality.CANDIDATE,
            reason="OFFICIAL_AVISO_AOS_ACIONISTAS",
        )

    return MaterialityDecision(
        materiality=Materiality.NON_MATERIAL,
        reason="OFFICIAL_OTHER",
    )


def _normalize(value: str) -> str:
    text = value.casefold().strip()
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))
