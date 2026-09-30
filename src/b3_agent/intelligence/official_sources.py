from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_evidence import OfficialEvidenceBuilder
from b3_agent.knowledge.evidence import Evidence
from b3_agent.providers.cvm_open_data import CvmOpenDataProvider


@dataclass(frozen=True)
class OfficialEvidenceSnapshot:
    by_ticker: dict[str, tuple[Evidence, ...]]
    coverage: dict[str, Any]


def load_open_data_official_evidence(
    tickers: tuple[str, ...] | list[str],
    *,
    year: int | None = None,
    provider: CvmOpenDataProvider | None = None,
    registry: IssuerRegistry | None = None,
) -> OfficialEvidenceSnapshot:
    """Load one CVM Open Data snapshot for a group of B3 tickers.

    CAD + FCA establish deterministic issuer identity. IPE is downloaded once
    for the selected year and filtered to the resolved CVM issuer codes.
    """
    normalized = tuple(
        dict.fromkeys(str(ticker).upper().strip() for ticker in tickers if str(ticker).strip())
    )
    if not normalized:
        raise ValueError("at least one ticker is required")

    target_year = year or datetime.now(timezone.utc).year
    provider = provider or CvmOpenDataProvider()
    registry = registry or IssuerRegistry()
    sync = registry.sync_from_cvm(provider=provider, year=target_year)

    resolved: dict[str, str] = {}
    cvm_codes: list[str] = []
    unresolved: list[str] = []

    for ticker in normalized:
        issuer = registry.resolve_issuer_by_ticker(ticker)
        if issuer is None:
            unresolved.append(ticker)
            continue
        resolved[ticker] = issuer.issuer_id
        if issuer.cvm_code and issuer.cvm_code not in cvm_codes:
            cvm_codes.append(issuer.cvm_code)

    if not cvm_codes:
        raise RuntimeError("issuer registry resolved no CVM codes for requested tickers")

    ipe = provider.fetch_ipe_year(
        target_year,
        cvm_codes=tuple(cvm_codes),
    )
    builder = OfficialEvidenceBuilder(registry=registry)
    by_ticker: dict[str, list[Evidence]] = {ticker: [] for ticker in normalized}
    material_total = 0
    candidate_total = 0

    for record in ipe.records:
        evidence = builder.from_open_data_ipe(record)
        if evidence.metadata.materiality == "MATERIAL":
            material_total += 1
        elif evidence.metadata.materiality == "CANDIDATE":
            candidate_total += 1

        for ticker in evidence.metadata.ticker_refs:
            if ticker in by_ticker:
                by_ticker[ticker].append(evidence)

    coverage = {
        "status": "SUCCESS" if not unresolved else "PARTIAL",
        "year": target_year,
        "registry_sync": sync,
        "requested_tickers": len(normalized),
        "resolved_tickers": len(resolved),
        "unresolved_tickers": unresolved,
        "ipe_document_count": len(ipe.records),
        "ipe_material_count": material_total,
        "ipe_candidate_count": candidate_total,
        "source_url": ipe.source_url,
        "pit_status": "HISTORICAL_RECONSTRUCTION",
    }
    return OfficialEvidenceSnapshot(
        by_ticker={key: tuple(value) for key, value in by_ticker.items()},
        coverage=coverage,
    )
