#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from b3_agent.jobs.cvm_disclosures import CvmDisclosureJob
from b3_agent.providers.cvm_rad import CvmRadCredentialsMissing
from b3_agent.providers.searxng_news import SearxngNewsAdapter


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="WEGE3")
    parser.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    requested_date = date.fromisoformat(args.date)
    now = datetime.now(timezone.utc)

    news = SearxngNewsAdapter()
    records = news.search(
        ticker,
        query=f"{ticker} notícias fato relevante resultados dividendos mercado",
        limit=20,
    )
    diagnostics = news.last_diagnostics
    cutoff = now.date() - timedelta(days=3)
    dated = [record for record in records if record.published_date is not None]
    recent = [
        record for record in dated
        if record.published_date is not None and record.published_date >= cutoff
    ]

    output = {
        "as_of": now.isoformat(),
        "ticker": ticker,
        "searxng": {
            "status": "SUCCESS" if records and dated else "COVERAGE_INSUFFICIENT",
            "records": len(records),
            "dated": len(dated),
            "recent_3d": len(recent),
            "fallback_used": diagnostics.fallback_used if diagnostics else None,
            "fallback_strategy": diagnostics.fallback_strategy if diagnostics else None,
            "primary_raw_results": diagnostics.primary_raw_result_count if diagnostics else None,
            "fallback_raw_results": diagnostics.fallback_raw_result_count if diagnostics else None,
            "unresponsive_engines": (
                list(diagnostics.unresponsive_engines) if diagnostics else []
            ),
            "sample": [
                {
                    "title": record.headline,
                    "published_at": (
                        record.published_at.isoformat()
                        if record.published_at
                        else None
                    ),
                    "source_name": record.source_name,
                    "url": record.url,
                }
                for record in records[:5]
            ],
        },
    }

    exit_code = 0
    try:
        cvm = CvmDisclosureJob().run(requested_date=requested_date)
        output["cvm_rad"] = {
            "status": cvm["acquisition_status"],
            "requested_date": cvm["requested_date"],
            "document_count": cvm["document_count"],
            "material_count": cvm["material_count"],
            "candidate_count": cvm["candidate_count"],
            "non_material_count": cvm["non_material_count"],
            "source_error_code": cvm["source_error_code"],
            "sample": [
                {
                    "cvm_code": row["cvm_code"],
                    "category": row["category"],
                    "source_status": row["source_status"],
                    "materiality": row["materiality"],
                    "materiality_reason": row["materiality_reason"],
                }
                for row in cvm["disclosures"][:5]
            ],
        }
    except CvmRadCredentialsMissing:
        output["cvm_rad"] = {
            "status": "CREDENTIALS_MISSING",
            "message": (
                "Configure CVM_DM_USER/CVM_DM_PASS in B3 runtime secrets; "
                "credentials were not printed."
            ),
        }
        exit_code = max(exit_code, 3)
    except Exception as exc:
        output["cvm_rad"] = {
            "status": "FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }
        exit_code = max(exit_code, 2)

    if output["searxng"]["status"] != "SUCCESS":
        exit_code = max(exit_code, 2)

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
