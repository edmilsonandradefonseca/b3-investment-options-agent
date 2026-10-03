#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from b3_agent.intelligence.official_sources import load_open_data_official_evidence
from b3_agent.jobs.nightly_intelligence import NightlyIntelligenceJob, portfolio_tickers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", action="append", dest="tickers")
    parser.add_argument("--news-limit", type=int, default=8)
    args = parser.parse_args()

    selected = args.tickers or portfolio_tickers()
    if not selected:
        raise RuntimeError("no portfolio tickers available for nightly intelligence")

    try:
        official_snapshot = load_open_data_official_evidence(selected)
        official_map = official_snapshot.by_ticker
        official_coverage = official_snapshot.coverage
    except Exception as exc:
        official_map = {}
        official_coverage = {
            "status": "FAILED",
            "requested_tickers": len(selected),
            "resolved_tickers": 0,
            "unresolved_tickers": list(selected),
            "error": f"{type(exc).__name__}: {exc}",
        }

    result = NightlyIntelligenceJob(
        news_limit=args.news_limit,
        local_analysis_mode="enqueue",
    ).run(
        tickers=list(selected),
        official_evidence_by_ticker=official_map,
    )
    from b3_agent.jobs.primary_targets import PrimaryTargetRefreshJob
    reviewed=ROOT/'docs'/'research'/'institution_targets_reviewed.json'
    target_refresh=PrimaryTargetRefreshJob().run(reviewed,tickers=list(selected)) if reviewed.exists() else {'status':'NO_REVIEWED_SOURCES'}
    output = {
        'institution_target_refresh':target_refresh,
        "ticker_count": result["ticker_count"],
        "completed": result["completed"],
        "skipped": result["skipped"],
        "deferred": result["deferred"],
        "coverage_insufficient": result["coverage_insufficient"],
        "failed": result["failed"],
        "deepseek_calls": result["deepseek_calls"],
        "local_analysis_mode": result["local_analysis_mode"],
        "local_analysis_enqueues": result["local_analysis_enqueues"],
        "queued_local_analysis": result["queued_local_analysis"],
        "official_sources": official_coverage,
        "as_of": result["as_of"],
    }
    print(json.dumps(output, ensure_ascii=False))

    official_ok = official_coverage.get("status") == "SUCCESS"
    # COVERAGE_INSUFFICIENT is an explicit V4.2/V4.3 evidence state, not a
    # runtime failure. The nightly producer succeeds as long as official-source
    # loading is healthy and no ticker execution failed.
    return 0 if official_ok and not result["failed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
