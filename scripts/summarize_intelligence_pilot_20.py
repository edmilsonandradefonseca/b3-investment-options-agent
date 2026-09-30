#!/usr/bin/env python3
"""Audit V4.2 20-stock pilot without rerunning providers or models."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def evaluate(root: Path) -> dict:
    manifest = json.loads((root / "latest.json").read_text(encoding="utf-8"))
    rows = manifest.get("results", [])
    issues = []
    coverage_gaps = []
    official = manifest.get("official_sources") or {}
    if manifest.get("requested") != 20 or len(rows) != 20 or len({r.get("ticker") for r in rows}) != 20:
        issues.append("20 distinct stocks were not processed")
    if official.get("status") != "SUCCESS":
        issues.append(f"official CVM coverage status is {official.get('status')}")
    if official.get("resolved_tickers") != 20:
        issues.append(
            f"issuer registry resolved {official.get('resolved_tickers')} of 20 tickers"
        )
    for item in rows:
        ticker = item.get("ticker")
        detail_path = root / f"{ticker}.json"
        if not detail_path.is_file():
            issues.append(f"{ticker}: missing audit artifact")
            continue
        detail = json.loads(detail_path.read_text(encoding="utf-8"))
        if detail.get("routes") != {"market": "market_provider", "research": "deepseek-r1:8b", "senior": "openclaw"}:
            issues.append(f"{ticker}: router mismatch")
        market = detail.get("market") or {}
        if not market.get("as_of") or not market.get("source"):
            issues.append(f"{ticker}: dated market evidence missing")
        elif (date.today() - date.fromisoformat(market["as_of"][:10])).days > 7:
            issues.append(f"{ticker}: market evidence older than 7 calendar days")
        local = detail.get("deepseek_status")
        senior = detail.get("openclaw_status")
        if local == "completed":
            if not detail.get("evidence", {}).get("source_refs"):
                issues.append(f"{ticker}: DeepSeek provenance missing")
            if senior != "completed":
                issues.append(f"{ticker}: material dossier not escalated successfully")
        elif local == "skipped_no_material_events":
            evidence = detail.get("evidence", {})
            if evidence.get("evidence_conclusion") != "NO_MATERIAL_FOUND":
                issues.append(f"{ticker}: no-material status without validated evidence conclusion")
            if not evidence.get("dated_result_count"):
                issues.append(f"{ticker}: no-material status without dated evidence coverage")
            if senior != "not_required":
                issues.append(f"{ticker}: unnecessary senior call")
        elif local == "coverage_insufficient":
            evidence = detail.get("evidence", {})
            if evidence.get("evidence_conclusion") != "COVERAGE_INSUFFICIENT":
                issues.append(
                    f"{ticker}: coverage-insufficient status without matching conclusion"
                )
            else:
                coverage_gaps.append(
                    {
                        "ticker": ticker,
                        "acquisition_status": evidence.get("acquisition_status"),
                        "raw_result_count": evidence.get("raw_result_count", 0),
                        "dated_result_count": evidence.get("dated_result_count", 0),
                        "dated_recent_count": evidence.get("dated_recent_count", 0),
                        "fallback_used": evidence.get("fallback_used", False),
                        "fallback_strategy": evidence.get("fallback_strategy"),
                        "engine_errors": evidence.get("engine_errors", []),
                    }
                )
        else:
            issues.append(f"{ticker}: research status {local}")
    deepseek_calls = sum(r.get("deepseek") == "completed" for r in rows)
    senior_calls = sum(r.get("openclaw") == "completed" for r in rows)
    status = (
        "LIMITED"
        if issues
        else "PASS_WITH_COVERAGE_GAPS"
        if coverage_gaps
        else "PASS"
    )
    return {
        "status": status,
        "stocks": len(rows), "router_verified": manifest.get("router_verified"),
        "market_validated": manifest.get("market_validated"),
        "official_sources_status": official.get("status"),
        "official_resolved_tickers": official.get("resolved_tickers"),
        "official_ipe_documents": official.get("ipe_document_count"),
        "official_ipe_material": official.get("ipe_material_count"),
        "deepseek_completed": deepseek_calls,
        "openclaw_escalations_completed": senior_calls,
        "skipped_no_material_events": sum(r.get("deepseek") == "skipped_no_material_events" for r in rows),
        "coverage_insufficient": sum(r.get("deepseek") == "coverage_insufficient" for r in rows),
        "coverage_gaps": coverage_gaps,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("/opt/b3-runtime/data/derived/intelligence_pilot_v42"))
    args = parser.parse_args()
    report = evaluate(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"PASS", "PASS_WITH_COVERAGE_GAPS"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
