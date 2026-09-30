from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_evidence import (
    OfficialEvidenceBuilder,
    evidence_to_dict,
)
from b3_agent.providers.cvm_rad import CvmRadDisclosureProvider


class CvmDisclosureJob:
    """Acquire, normalize and persist the current official CVM IPE feed."""

    def __init__(
        self,
        *,
        provider: CvmRadDisclosureProvider | None = None,
        registry: IssuerRegistry | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.provider = provider or CvmRadDisclosureProvider()
        self.registry = registry or IssuerRegistry()
        self.evidence_builder = OfficialEvidenceBuilder(registry=self.registry)
        self.output_dir = Path(
            output_dir or settings.data_dir / "derived" / "cvm_rad_disclosures"
        )

    def run(self, *, requested_date: date | None = None) -> dict[str, Any]:
        target_date = requested_date or datetime.now(timezone.utc).date()
        started_at = datetime.now(timezone.utc)
        result = self.provider.query_ipe(target_date)
        completed_at = datetime.now(timezone.utc)

        rows: list[dict[str, Any]] = []
        for disclosure in result.disclosures:
            evidence = self.evidence_builder.from_rad(disclosure)
            metadata = evidence.metadata
            rows.append(
                {
                    "provider_record_id": disclosure.provider_record_id,
                    "cvm_code": disclosure.cvm_code,
                    "issuer_ref": metadata.issuer_ref,
                    "ticker_refs": list(metadata.ticker_refs),
                    "document_type": disclosure.document_type,
                    "category": disclosure.category,
                    "disclosure_type": disclosure.disclosure_type,
                    "species": disclosure.species,
                    "reference_date": (
                        disclosure.reference_date.isoformat()
                        if disclosure.reference_date
                        else None
                    ),
                    "source_status": disclosure.source_status,
                    "document_url": disclosure.document_url,
                    "retrieved_at": disclosure.retrieved_at.isoformat(),
                    "materiality": metadata.materiality,
                    "materiality_reason": metadata.materiality_reason,
                    "materiality_policy_version": metadata.materiality_policy_version,
                    "pit_status": metadata.pit_status,
                    "evidence_id": evidence.evidence_id,
                    "evidence": evidence_to_dict(evidence),
                    "raw_attributes": disclosure.raw_attributes,
                }
            )

        manifest = {
            "provider": self.provider.name,
            "requested_date": target_date.isoformat(),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "acquisition_status": "SUCCESS",
            "source_error_code": result.source_error_code,
            "document_count": len(rows),
            "mapped_document_count": sum(bool(row["ticker_refs"]) for row in rows),
            "unmapped_document_count": sum(not row["ticker_refs"] for row in rows),
            "material_count": sum(row["materiality"] == "MATERIAL" for row in rows),
            "candidate_count": sum(row["materiality"] == "CANDIDATE" for row in rows),
            "non_material_count": sum(
                row["materiality"] == "NON_MATERIAL" for row in rows
            ),
            "disclosures": rows,
        }
        self._persist(manifest, completed_at=completed_at)
        return manifest

    def _persist(self, manifest: dict[str, Any], *, completed_at: datetime) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        runs = self.output_dir / "runs"
        runs.mkdir(parents=True, exist_ok=True)

        stamp = completed_at.strftime("%Y%m%dT%H%M%S%fZ")
        run_path = runs / f"{manifest['requested_date']}_{stamp}.json"
        run_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        latest = self.output_dir / "latest.json"
        temp = latest.with_suffix(".tmp")
        temp.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(latest)
