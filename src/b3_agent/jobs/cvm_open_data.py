from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_evidence import (
    OfficialEvidenceBuilder,
    evidence_to_dict,
)
from b3_agent.providers.cvm_open_data import CvmOpenDataProvider


class CvmOpenDataBackfillJob:
    """Backfill/reconcile official IPE history using zero-cost CVM Open Data."""

    def __init__(
        self,
        *,
        provider: CvmOpenDataProvider | None = None,
        registry: IssuerRegistry | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.provider = provider or CvmOpenDataProvider()
        self.registry = registry or IssuerRegistry()
        self.evidence_builder = OfficialEvidenceBuilder(registry=self.registry)
        self.output_dir = Path(
            output_dir or settings.data_dir / "derived" / "cvm_open_data_ipe"
        )

    def run(
        self,
        *,
        year: int,
        cvm_codes: tuple[str, ...] = (),
        cnpjs: tuple[str, ...] = (),
        categories: tuple[str, ...] = (),
        sync_registry: bool = True,
    ) -> dict[str, Any]:
        started_at = datetime.now(timezone.utc)

        registry_sync = None
        if sync_registry:
            registry_sync = self.registry.sync_from_cvm(
                provider=self.provider,
                year=year,
            )

        result = self.provider.fetch_ipe_year(
            year,
            cvm_codes=cvm_codes,
            cnpjs=cnpjs,
            categories=categories,
        )

        rows: list[dict[str, Any]] = []
        for record in result.records:
            evidence = self.evidence_builder.from_open_data_ipe(record)
            metadata = evidence.metadata
            rows.append(
                {
                    "provider_record_id": record.provider_record_id,
                    "protocol": record.protocol,
                    "version": record.version,
                    "cvm_code": record.cvm_code,
                    "cnpj": record.cnpj,
                    "issuer_ref": metadata.issuer_ref,
                    "ticker_refs": list(metadata.ticker_refs),
                    "company_name": record.company_name,
                    "category": record.category,
                    "disclosure_type": record.disclosure_type,
                    "species": record.species,
                    "subject": record.subject,
                    "reference_date": (
                        record.reference_date.isoformat()
                        if record.reference_date
                        else None
                    ),
                    "delivered_at": (
                        record.delivered_at.isoformat()
                        if record.delivered_at
                        else None
                    ),
                    "retrieved_at": record.retrieved_at.isoformat(),
                    "document_url": record.document_url,
                    "materiality": metadata.materiality,
                    "materiality_reason": metadata.materiality_reason,
                    "materiality_policy_version": metadata.materiality_policy_version,
                    "pit_status": metadata.pit_status,
                    "evidence_id": evidence.evidence_id,
                    "evidence": evidence_to_dict(evidence),
                }
            )

        completed_at = datetime.now(timezone.utc)
        manifest = {
            "provider": self.provider.name,
            "year": year,
            "source_url": result.source_url,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "acquisition_status": "SUCCESS",
            "pit_status": "HISTORICAL_RECONSTRUCTION",
            "filters": {
                "cvm_codes": list(cvm_codes),
                "cnpjs": list(cnpjs),
                "categories": list(categories),
            },
            "registry_sync": registry_sync,
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
        run_path = runs / f"{manifest['year']}_{stamp}.json"
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
