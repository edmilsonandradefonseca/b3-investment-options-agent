#!/usr/bin/env python3
"""Live V4.2 smoke for public/zero-cost official CVM sources.

Runs against CVM Open Data only; no CVM Download Multiplo credentials required.
It validates the real CAD -> FCA ticker registry -> IPE backfill path and prints
only non-secret operational diagnostics.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.config import settings
from b3_agent.intelligence.issuer_registry import IssuerRegistry
from b3_agent.intelligence.official_evidence import OfficialEvidenceBuilder
from b3_agent.providers.cvm_open_data import CvmOpenDataProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="PETR4")
    parser.add_argument("--year", type=int, default=date.today().year)
    parser.add_argument(
        "--registry",
        type=Path,
        default=settings.data_dir / "structured" / "issuer_registry.sqlite3",
    )
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    provider = CvmOpenDataProvider()
    registry = IssuerRegistry(args.registry)
    started_at = datetime.now(timezone.utc)

    try:
        sync = registry.sync_from_cvm(provider=provider, year=args.year)
        issuer = registry.resolve_issuer_by_ticker(ticker)
        if issuer is None:
            raise RuntimeError(f"issuer registry did not resolve ticker {ticker}")

        mapped = registry.resolve_tickers(
            cvm_code=issuer.cvm_code,
            cnpj=issuer.cnpj,
        )
        result = provider.fetch_ipe_year(
            args.year,
            cvm_codes=(issuer.cvm_code,) if issuer.cvm_code else (),
            cnpjs=(issuer.cnpj,) if issuer.cnpj else (),
        )
        builder = OfficialEvidenceBuilder(registry=registry)
        evidence = tuple(builder.from_open_data_ipe(record) for record in result.records)

        material = [item for item in evidence if item.metadata.materiality == "MATERIAL"]
        candidate = [item for item in evidence if item.metadata.materiality == "CANDIDATE"]
        mapped_evidence = [item for item in evidence if ticker in item.metadata.ticker_refs]

        output = {
            "status": "PASS",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker,
            "year": args.year,
            "registry": {
                "issuer_id": issuer.issuer_id,
                "cvm_code": issuer.cvm_code,
                "cnpj": issuer.cnpj,
                "legal_name": issuer.legal_name,
                "tickers": list(mapped),
                "sync": sync,
            },
            "ipe": {
                "source_url": result.source_url,
                "document_count": len(evidence),
                "ticker_mapped_document_count": len(mapped_evidence),
                "material_count": len(material),
                "candidate_count": len(candidate),
                "pit_statuses": sorted(
                    {item.metadata.pit_status for item in evidence if item.metadata.pit_status}
                ),
                "sample_material": [
                    {
                        "evidence_id": item.evidence_id,
                        "title": item.title,
                        "published_at": (
                            item.metadata.published_at.isoformat()
                            if item.metadata.published_at
                            else None
                        ),
                        "reference_at": (
                            item.metadata.reference_at.isoformat()
                            if item.metadata.reference_at
                            else None
                        ),
                        "ticker_refs": list(item.metadata.ticker_refs),
                        "materiality_reason": item.metadata.materiality_reason,
                        "source_url": item.source_url,
                    }
                    for item in material[:3]
                ],
            },
            "duration_seconds": (
                datetime.now(timezone.utc) - started_at
            ).total_seconds(),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "ticker": ticker,
                    "year": args.year,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
